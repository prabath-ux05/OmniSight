"""OmniSight Backend Configuration and Environment Settings."""

from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv

# Locate and load root .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings:
    """Centralized typed application settings loaded from environment variables."""

    def __init__(self) -> None:
        # Application Settings
        self.APP_ENV: str = os.getenv("APP_ENV", "development").lower()
        self.APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() in ("true", "1", "yes")
        self.API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
        self.API_PORT: int = int(os.getenv("API_PORT", "8000"))
        self.API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")

        # PostgreSQL Database Credentials
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "omnisight_user")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "omnisight_db")

        # Explicit database URLs
        self._raw_database_url: str | None = os.getenv("DATABASE_URL")
        self.TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_omnisight.db")

        # CORS Allowed Origins
        raw_cors = os.getenv("CORS_ORIGINS")
        if raw_cors:
            self.CORS_ORIGINS: list[str] = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]
        else:
            self.CORS_ORIGINS = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]

        # Authentication Session and Cookie Settings
        self.SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "omnisight_session")
        self.CSRF_COOKIE_NAME: str = os.getenv("CSRF_COOKIE_NAME", "omnisight_csrf")
        self.SESSION_EXPIRE_DAYS: int = int(os.getenv("SESSION_EXPIRE_DAYS", "7"))
        # In development/test, allow non-secure HTTP cookies; require secure cookies in production/staging
        self.COOKIE_SECURE: bool = os.getenv(
            "COOKIE_SECURE",
            "false" if self.APP_ENV in ("development", "test") else "true",
        ).lower() in ("true", "1", "yes")
        self.COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax").lower()
        self.COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN") or None
        self.COOKIE_PATH: str = "/"

        # CSRF Signing Secret Key: strictly required in production with >= 32 chars
        raw_csrf_secret = os.getenv("CSRF_SECRET_KEY")
        dev_placeholder = "omnisight-dev-insecure-csrf-secret-key-32b"

        if self.APP_ENV not in ("development", "test"):
            if not raw_csrf_secret or len(raw_csrf_secret.strip()) < 32 or raw_csrf_secret.strip() == dev_placeholder:
                raise ValueError(
                    "Production configuration error: CSRF_SECRET_KEY must be set in production "
                    "with at least 32 characters of high-entropy secret material."
                )
            self.CSRF_SECRET_KEY: str = raw_csrf_secret.strip()
        else:
            self.CSRF_SECRET_KEY: str = raw_csrf_secret.strip() if raw_csrf_secret else dev_placeholder

    @property
    def DATABASE_URL(self) -> str:
        """Return the active database connection string based on the running environment."""
        if self.APP_ENV == "test":
            return self.TEST_DATABASE_URL

        if self._raw_database_url:
            # Normalize postgres:// to postgresql+psycopg2:// if needed
            url = self._raw_database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg2" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url

        # Construct PostgreSQL connection string from components
        password_part = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}{password_part}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


settings = get_settings()
