"""Integration fixtures for Microsoft SQL Server real database tests."""

import os
from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, text

from src.infrastructure.persistence.mssql.connection import (
    create_mssql_engine,
    create_session_factory,
)

MSSQL_TEST_URL = os.getenv(
    "DATABASE_URL",
    "mssql+pymssql://sa:YourStrong%40Password123@localhost:1433/ChatbotDB",
)


@pytest.fixture(scope="session")
def mssql_engine() -> Generator[Engine, None, None]:
    """Provide a session-scoped engine connected to the running SQL Server container."""
    try:
        engine = create_mssql_engine(MSSQL_TEST_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"SQL Server container not reachable at {MSSQL_TEST_URL}: {exc}")

    # Ensure tables exist
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_db(mssql_engine: Engine) -> Generator[None, None, None]:
    """Clean all tables before and after each integration test."""

    def _truncate_tables() -> None:
        import time

        for attempt in range(3):
            with Session(mssql_engine) as session:
                try:
                    session.execute(text("DELETE FROM pii_audit_logs"))
                    session.execute(text("DELETE FROM security_incidents"))
                    session.execute(text("DELETE FROM workflow_checkpoints"))
                    session.execute(text("DELETE FROM workflow_instances"))
                    session.execute(text("DELETE FROM tool_execution_audits"))
                    session.execute(text("DELETE FROM tool_approvals"))
                    session.execute(text("DELETE FROM knowledge_document_chunks"))
                    session.execute(text("DELETE FROM knowledge_documents"))
                    session.execute(text("DELETE FROM stream_buffer_chunks"))
                    session.execute(text("DELETE FROM messages"))
                    session.execute(text("DELETE FROM outbox_messages"))
                    session.execute(text("DELETE FROM conversations"))
                    session.execute(text("DELETE FROM audit_logs"))
                    session.execute(text("DELETE FROM idempotency_keys"))
                    session.execute(text("DELETE FROM tenant_policies"))
                    session.execute(text("DELETE FROM tenants"))
                    session.commit()
                    return
                except Exception:
                    session.rollback()
                    if attempt == 2:
                        raise
                    time.sleep(0.1)

    _truncate_tables()
    yield
    _truncate_tables()


@pytest.fixture
def mssql_session(mssql_engine: Engine, clean_db: None) -> Generator[Session, None, None]:
    """Provide a clean SQLModel session bound to real MSSQL."""
    factory = create_session_factory(mssql_engine)
    with factory() as session:
        yield session
