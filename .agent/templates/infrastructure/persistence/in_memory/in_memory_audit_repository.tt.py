"""Template canónico para InMemoryAuditRepositoryAdapter.

Reglas:
- Pertenece a src/infrastructure/persistence/in_memory/.
- Implementa AuditRepositoryPort.
- Almacenamiento volátil para tests unitarios y desarrollo local.
"""

from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.entities.audit_log_record import AuditLogRecord


class InMemoryAuditRepositoryAdapter(AuditRepositoryPort):
    """Adaptador de infraestructura en memoria para el repositorio de auditoría."""

    def __init__(self) -> None:
        self._records: list[AuditLogRecord] = []

    async def record(self, log_entry: AuditLogRecord) -> None:
        self._records.append(log_entry)

    async def list_by_resource(
        self, resource_type: str, resource_id: str
    ) -> list[AuditLogRecord]:
        return [
            entry
            for entry in self._records
            if entry.resource_type == resource_type and entry.resource_id == resource_id
        ]

    def all_records(self) -> list[AuditLogRecord]:
        """Método helper para inspección en tests."""
        return list(self._records)
