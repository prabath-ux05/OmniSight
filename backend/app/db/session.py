"""Database session and engine management for OmniSight."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.base_class import Base


class DatabaseConnectionError(Exception):
    """Raised when the database connection fails or service is unreachable."""
    pass


def create_app_engine(database_url: str):
    """Create a SQLAlchemy engine configured appropriately for the target dialect."""
    if database_url.startswith("sqlite"):
        eng = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Primary application engine and session factory
engine = create_app_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def init_db(bind_engine=None) -> None:
    """Initialize database tables according to registered ORM models."""
    target = bind_engine or engine
    Base.metadata.create_all(bind=target)
    logger.info("Initialized database tables on engine: %s", target.url)


def check_db_connection(bind_engine=None) -> bool:
    """Verify that the database engine can successfully connect and execute a ping query."""
    target = bind_engine or engine
    try:
        with target.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except (OperationalError, DBAPIError) as exc:
        logger.error("Database connection check failed on %s: %s", target.url, str(exc))
        return False
    except Exception as exc:
        logger.error("Unexpected database error on %s: %s", target.url, str(exc))
        return False


def get_db() -> Generator[Session, None, None]:
    """FastAPI request dependency yielding an isolated database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session(session_factory=None) -> Generator[Session, None, None]:
    """Context manager for safe transactional database sessions with automatic commit/rollback."""
    factory = session_factory or SessionLocal
    db = factory()
    try:
        yield db
        db.commit()
    except (OperationalError, DBAPIError) as exc:
        db.rollback()
        logger.error("Database error during transaction: %s", str(exc))
        raise DatabaseConnectionError(f"Database operational failure: {str(exc)}") from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
