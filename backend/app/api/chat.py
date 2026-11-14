"""FastAPI router for OmniSight LLM conversational assistant."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_current_user_optional
from backend.app.core.logging import logger
from backend.app.models.user import UserModel
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
)
from backend.app.schemas.errors import ErrorResponse
from backend.app.services.chat_service import chat_service

router = APIRouter(prefix="/api/v1/chat", tags=["LLM Assistant"])


@router.get(
    "/status",
    response_model=ChatStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get LLM Assistant readiness status",
    description=(
        "Checks whether the backend is configured with valid LLM credentials (Gemini/OpenAI) "
        "and returns current provider and model metadata without exposing secrets."
    ),
)
def get_chat_status() -> ChatStatusResponse:
    """Retrieve the LLM readiness and provider status."""
    return chat_service.get_status()


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a conversational query to the OmniSight LLM Assistant",
    description=(
        "Processes an open-ended natural-language question with multi-turn conversation history "
        "and active inspection run/finding/repair context. Supports both authenticated and guest users."
    ),
    responses={
        200: {"model": ChatResponse, "description": "LLM response generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid chat request payload"},
        429: {"model": ErrorResponse, "description": "AI provider rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "AI provider gateway or authentication error"},
        503: {"model": ErrorResponse, "description": "LLM Chat not configured (missing backend API key)"},
        504: {"model": ErrorResponse, "description": "AI provider request timed out"},
    },
)
def chat_completion(
    request: ChatRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> ChatResponse:
    """Execute LLM chat completion with context grounding."""
    user_label = current_user.email if current_user else "guest"
    logger.info("Processing chat query from user '%s': %r", user_label, request.message[:80])
    return chat_service.send_chat_message(request)
