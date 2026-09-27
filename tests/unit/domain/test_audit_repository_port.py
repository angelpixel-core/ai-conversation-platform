"""Unit contract tests for AuditRepositoryPort."""

import pytest

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort


class FakeAuditRepository(AuditRepositoryPort):
    """Fake repository to test adherence to AuditRepositoryPort contract."""

    def __init__(self) -> None:
        self.entries: list[AuditLogRecord] = []

    async def record(self, log_entry: AuditLogRecord) -> None:
        self.entries.append(log_entry)

    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditLogRecord]:
        return [
            entry
            for entry in self.entries
            if entry.resource_type == resource_type and entry.resource_id == resource_id
        ]


@pytest.mark.anyio
async def test_audit_repository_port_contract() -> None:
    repo = FakeAuditRepository()
    assert isinstance(repo, AuditRepositoryPort)

    log1 = AuditLogRecord.create(
        event_name="message_sent",
        actor_id="u-1",
        resource_type="conversation",
        resource_id="conv-1",
        action="append",
        tokens_consumed=15,
    )
    log2 = AuditLogRecord.create(
        event_name="message_sent",
        actor_id="u-2",
        resource_type="conversation",
        resource_id="conv-2",
        action="append",
        tokens_consumed=25,
    )

    await repo.record(log1)
    await repo.record(log2)

    results = await repo.list_by_resource("conversation", "conv-1")
    assert len(results) == 1
    assert results[0].id == log1.id
    assert results[0].tokens_consumed == 15
