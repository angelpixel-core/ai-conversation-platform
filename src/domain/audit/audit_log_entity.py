"""Domain Entity for AuditLogRecord in DDD.

Rules:
- Immutable by design (@dataclass(frozen=True)).
- Represents an immutable transactional audit record for operations, events, and token consumption.
- Zero external framework dependencies (standard library only).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditLogRecord:
    """Immutable domain entity representing an audit log entry."""

    id: uuid.UUID
    event_name: str
    actor_id: str
    resource_type: str
    resource_id: str
    action: str
    payload: dict[str, Any]
    tokens_consumed: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        clean_event = self.event_name.strip() if self.event_name else ""
        if not clean_event:
            raise ValueError("El nombre del evento de auditoría no puede estar vacío.")

        clean_actor = self.actor_id.strip() if self.actor_id else ""
        if not clean_actor:
            raise ValueError("El identificador del actor no puede estar vacío.")

        clean_resource_type = self.resource_type.strip() if self.resource_type else ""
        if not clean_resource_type:
            raise ValueError("El tipo de recurso no puede estar vacío.")

        clean_resource_id = self.resource_id.strip() if self.resource_id else ""
        if not clean_resource_id:
            raise ValueError("El ID del recurso no puede estar vacío.")

        clean_action = self.action.strip() if self.action else ""
        if not clean_action:
            raise ValueError("La acción auditada no puede estar vacía.")

        if self.tokens_consumed < 0:
            raise ValueError("El consumo de tokens no puede ser negativo.")

        object.__setattr__(self, "event_name", clean_event)
        object.__setattr__(self, "actor_id", clean_actor)
        object.__setattr__(self, "resource_type", clean_resource_type)
        object.__setattr__(self, "resource_id", clean_resource_id)
        object.__setattr__(self, "action", clean_action)

        if self.occurred_at.tzinfo is None:
            object.__setattr__(self, "occurred_at", self.occurred_at.replace(tzinfo=UTC))

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
        """Factory method to construct a new AuditLogRecord with UUIDv4 and UTC timestamp."""
        return cls(
            id=uuid.uuid4(),
            event_name=event_name,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            payload=payload or {},
            tokens_consumed=tokens_consumed,
            occurred_at=datetime.now(UTC),
        )
