"""Unit tests for MSSQL connection and session factory."""

from sqlalchemy.engine import Engine
from sqlmodel import Session, text

from src.infrastructure.persistence.mssql.connection import (
    create_mssql_engine,
    create_session_factory,
)


def test_create_engine_with_sqlite_memory() -> None:
    """Validate engine creation for SQLite in-memory."""
    engine = create_mssql_engine("sqlite:///:memory:")
    assert isinstance(engine, Engine)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_create_engine_with_mssql_url() -> None:
    """Validate engine creation with MSSQL connection string parameters."""
    url = "mssql+pymssql://sa:YourStrong%40Password123@localhost:1433/ChatbotDB"
    engine = create_mssql_engine(
        url=url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=15,
        pool_recycle=1800,
        echo=False,
    )
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "mssql+pymssql"
    assert engine.url.database == "ChatbotDB"


def test_create_session_factory_returns_session() -> None:
    """Validate session factory returns active SQLModel Session."""
    engine = create_mssql_engine("sqlite:///:memory:")
    session_factory = create_session_factory(engine)

    session = session_factory()
    try:
        assert isinstance(session, Session)
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        session.close()
