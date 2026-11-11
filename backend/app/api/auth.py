"""FastAPI authentication router for OmniSight.

Exposes endpoints for email/password registration, login, current-user profile,
and secure session revocation (logout).
Enforces HTTP-only session cookies, CSRF protection, and trusted origin validation.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    clear_auth_cookies,
    extract_session_token,
    get_current_user_required,
    get_db,
    set_auth_cookies,
    validate_csrf,
    validate_trusted_origin,
)
from backend.app.core.logging import logger
from backend.app.core.security import generate_csrf_token
from backend.app.models.user import UserModel
from backend.app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserProfileResponse,
    UserResponse,
)
from backend.app.services.auth_service import (
    DuplicateEmailError,
    InactiveAccountError,
    InvalidCredentialsError,
    auth_service,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user account with email and password, creates an active session, and sets authentication cookies.",
)
def register(
    request: Request,
    response: Response,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account and initialize an authenticated session."""
    validate_trusted_origin(request)

    try:
        user = auth_service.register_user(db, payload)
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    session_record, raw_token = auth_service.create_session(
        db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    csrf_token = generate_csrf_token(session_record.session_token_hash)
    set_auth_cookies(response, session_token=raw_token, csrf_token=csrf_token)

    return auth_service.user_to_response(user)


@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user login",
    description="Authenticates email and password credentials, creates a fresh session, and sets authentication cookies.",
)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Authenticate credentials and initialize an active user session."""
    validate_trusted_origin(request)

    try:
        user = auth_service.authenticate_user(db, payload)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveAccountError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended.",
        )

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    session_record, raw_token = auth_service.create_session(
        db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    csrf_token = generate_csrf_token(session_record.session_token_hash)
    set_auth_cookies(response, session_token=raw_token, csrf_token=csrf_token)

    return auth_service.user_to_response(user)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description="Returns public profile and linked providers for the caller's active session. Requires valid authentication.",
)
def get_current_user_profile(
    current_user: UserModel = Depends(get_current_user_required),
) -> UserProfileResponse:
    """Retrieve public profile information for the actively authenticated caller."""
    return auth_service.user_to_response(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out and revoke current session",
    description="Revokes the active session from the database and clears authentication cookies. Safe on repeated invocation.",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revoke caller's database session and clear authentication cookies."""
    validate_csrf(request, db=db)

    token = extract_session_token(request)
    if token:
        auth_service.revoke_session(db, token)

    clear_auth_cookies(response)
    logger.info("Caller completed logout and cookies cleared.")
    return {"message": "Logged out successfully."}
