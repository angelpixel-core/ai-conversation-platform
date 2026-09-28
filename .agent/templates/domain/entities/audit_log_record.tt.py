"""Template canónico para la Entidad de Dominio AuditLogRecord (DDD).

Reglas:
- Inmutable por diseño (@dataclass(frozen=True)).
- Representa un registro de auditoría transaccional para trazabilidad y cobro de tokens.
- Sin dependencias de frameworks externos.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(frozen=True)
class AuditLogRecord:
    """Entidad de dominio inmutable para auditoría de acciones del sistema."""

    id: uuid.UUID
    event_name: str
    actor_id: str
    resource_type: str
    resource_id: str
    action: str
    payload: dict[str, Any]
    tokens_consumed: int
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.event_name or not self.event_name.strip():
            raise ValueError("El nombre del evento de auditoría no puede estar vacío.")
        if not self.actor_id or not self.actor_id.strip():
            raise ValueError("El identificador del actor no puede estar vacío.")
        if not self.resource_type or not self.resource_type.strip():
            raise ValueError("El tipo de recurso no puede estar vacío.")
        if not self.resource_id or not self.resource_id.strip():
            raise ValueError("El ID del recurso no puede estar vacío.")
        if not self.action or not self.action.strip():
            raise ValueError("La acción auditada no puede estar vacía.")
        if self.tokens_consumed < 0:
            raise ValueError("El consumo de tokens no puede ser negativo.")

        if self.occurred_at.tzinfo is None:
            object.__setattr__(
                self, "occurred_at", self.occurred_at.replace(tzinfo=timezone.utc)
            )

    @classmethod
    def create(
        cls,
        event_name: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
        tokens_consumed: int = 0,
    ) -> "AuditLogRecord":
        return cls(
            id=uuid.uuid4(),
            event_name=event_name.strip(),
            actor_id=actor_id.strip(),
            resource_type=resource_type.strip(),
            resource_id=resource_id.strip(),
            action=action.strip(),
            payload=payload or {},
            tokens_consumed=tokens_consumed,
            occurred_at=datetime.now(timezone.utc),
        )
