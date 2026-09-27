"""Domain Port for Audit Repository in DDD.

Rules:
- Belongs to src/domain/audit/ports/.
- Pure abstraction for appending and querying immutable audit logs.
- Zero external framework dependencies.
"""

from abc import ABC, abstractmethod

from src.domain.audit.audit_log_entity import AuditLogRecord


class AuditRepositoryPort(ABC):
    """Abstract driven port for persisting and querying audit log records."""

    @abstractmethod
    async def record(self, log_entry: AuditLogRecord) -> None:
        """Persist an immutable audit record."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditLogRecord]:
        """Query audit history for a specific resource type and identifier."""
        raise NotImplementedError
