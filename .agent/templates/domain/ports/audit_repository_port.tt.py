"""Template canónico para el Puerto del Repositorio de Auditoría (Domain Port).

Reglas:
- Pertenece a src/domain/audit/ports/.
- Abstracción pura para persistencia inmutable de registros de auditoría.
- Sin dependencias de frameworks o bases de datos específicas.
"""

from abc import ABC, abstractmethod

from src.domain.entities.audit_log_record import AuditLogRecord


class AuditRepositoryPort(ABC):
    """Puerto de repositorio para almacenar y consultar registros de auditoría."""

    @abstractmethod
    async def record(self, log_entry: AuditLogRecord) -> None:
        """Persiste un registro inmutable de auditoría."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_resource(
        self, resource_type: str, resource_id: str
    ) -> list[AuditLogRecord]:
        """Obtiene la traza de auditoría histórica para un recurso específico."""
        raise NotImplementedError
