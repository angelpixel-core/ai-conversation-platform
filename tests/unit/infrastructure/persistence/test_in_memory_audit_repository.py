"""Unit tests for InMemoryAuditRepositoryAdapter."""

import pytest

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.infrastructure.persistence.in_memory.in_memory_audit_repository import (
    InMemoryAuditRepositoryAdapter,
)


@pytest.mark.anyio
async def test_in_memory_audit_repository_records_and_queries() -> None:
    repo = InMemoryAuditRepositoryAdapter()
    assert isinstance(repo, AuditRepositoryPort)

    entry1 = AuditLogRecord.create(
        event_name="token_usage",
        actor_id="user-1",
        resource_type="chat",
        resource_id="chat-1",
        action="infer",
        tokens_consumed=120,
    )
    entry2 = AuditLogRecord.create(
        event_name="token_usage",
        actor_id="user-1",
        resource_type="chat",
        resource_id="chat-2",
        action="infer",
        tokens_consumed=80,
    )

    await repo.record(entry1)
    await repo.record(entry2)

    assert len(repo.all_records()) == 2

    chat1_audits = await repo.list_by_resource("chat", "chat-1")
    assert len(chat1_audits) == 1
    assert chat1_audits[0].tokens_consumed == 120
