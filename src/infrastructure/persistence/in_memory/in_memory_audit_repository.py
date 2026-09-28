"""In-memory implementation of the AuditRepositoryPort.

Rules:
- Belongs to src/infrastructure/persistence/in_memory/.
- Implements AuditRepositoryPort.
- Provides volatile in-memory storage for unit tests and local development.
"""

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort


class InMemoryAuditRepositoryAdapter(AuditRepositoryPort):
    """In-memory adapter for the domain audit repository port."""

    def __init__(self) -> None:
        self._records: list[AuditLogRecord] = []

    async def record(self, log_entry: AuditLogRecord) -> None:
        self._records.append(log_entry)

    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditLogRecord]:
        return [
            entry
            for entry in self._records
            if entry.resource_type == resource_type and entry.resource_id == resource_id
        ]

    def all_records(self) -> list[AuditLogRecord]:
        """Inspection helper for unit tests."""
        return list(self._records)
