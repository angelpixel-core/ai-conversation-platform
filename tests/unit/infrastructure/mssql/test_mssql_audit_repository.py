"""Unit tests for MssqlAuditRepositoryAdapter adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.infrastructure.persistence.mssql.audit_repository import (
    MssqlAuditRepositoryAdapter,
)


@pytest.fixture(name="session")
def fixture_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.anyio
async def test_mssql_audit_repository_records_and_queries(session: Session) -> None:
    repo = MssqlAuditRepositoryAdapter(session=session)
    assert isinstance(repo, AuditRepositoryPort)

    entry1 = AuditLogRecord.create(
        event_name="token_usage",
        actor_id="user-1",
        resource_type="chat",
        resource_id="chat-100",
        action="infer",
        tokens_consumed=100,
        payload={"model": "gpt-4"},
    )
    entry2 = AuditLogRecord.create(
        event_name="token_usage",
        actor_id="user-1",
        resource_type="chat",
        resource_id="chat-200",
        action="infer",
        tokens_consumed=50,
    )

    await repo.record(entry1)
    await repo.record(entry2)

    chat100_logs = await repo.list_by_resource("chat", "chat-100")
    assert len(chat100_logs) == 1
    assert chat100_logs[0].tokens_consumed == 100
    assert chat100_logs[0].payload == {"model": "gpt-4"}
