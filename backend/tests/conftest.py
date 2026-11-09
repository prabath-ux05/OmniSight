"""Pytest configuration and test isolation fixtures for OmniSight Backend."""

import os
from pathlib import Path
import pytest

# Force isolated test environment before any application imports
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_omnisight.db"

from backend.app.db.session import engine, init_db
from backend.app.services.run_store import run_store


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create database tables on isolated test SQLite database and clean up after session."""
    init_db(engine)
    yield
    test_db = Path("test_omnisight.db")
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clean_run_store():
    """Ensure database state is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()
