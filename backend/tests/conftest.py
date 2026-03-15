"""Pytest configuration and shared fixtures.

Testing approach:
- Uses a separate in-memory (or temp-file) SQLite database per test session.
- Provides a db fixture (Session) and a client fixture (FastAPI TestClient).
- Connectors and LLM calls are stubbed/monkeypatched — tests never call
  external APIs.
- Service-level unit tests use the db fixture directly.
- Route-level integration tests use the client fixture.

TODO: implement fixtures once models and services are built
"""
import pytest


@pytest.fixture
def db():
    # TODO: create in-memory SQLite engine; create all tables; yield session; drop all
    raise NotImplementedError


@pytest.fixture
def client(db):
    # TODO: override get_db dependency with test db session; return TestClient(app)
    raise NotImplementedError
