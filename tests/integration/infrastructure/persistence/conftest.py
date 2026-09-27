"""Integration test fixtures for persistence and Outbox Relay tests."""

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine

from src.infrastructure.persistence.mssql.connection import create_session_factory
from tests.integration.infrastructure.mssql.conftest import (
    clean_db,
    mssql_engine,
)

__all__ = ["clean_db", "mssql_engine", "mssql_session_factory"]


@pytest.fixture
def mssql_session_factory(mssql_engine: Engine) -> Generator:
    """Provide a session factory for real MSSQL."""
    factory = create_session_factory(mssql_engine)
    yield factory
