"""Pytest configuration and shared fixtures.

Testing approach:
- Uses an in-memory SQLite database per test function.
- Provides a db fixture (Session) and a client fixture (FastAPI TestClient).
- VaultReader is stubbed via mock_vault so tests never touch the filesystem.
- Service-level unit tests use the db fixture directly.
- Route-level tests use the client fixture.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all ORM models with SQLAlchemy mapper
from app.db.session import get_db
from app.main import app
from app.models.base import Base


@pytest.fixture
def db():
    """Isolated in-memory SQLite session; tables are created fresh and dropped after each test.

    StaticPool forces all connections (including the TestClient's worker thread)
    to share the same in-memory database, so the tables created here are visible
    inside request handlers.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_vault():
    """Stub VaultReader so experience tests never touch the real filesystem."""
    vault = MagicMock()
    vault.experience_path_exists.return_value = True
    vault.read_experience_file.return_value = ""
    with patch("app.services.experience_service.VaultReader", return_value=vault):
        yield vault


@pytest.fixture
def client(db, mock_vault):
    """TestClient wired to the test db session with VaultReader stubbed."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
