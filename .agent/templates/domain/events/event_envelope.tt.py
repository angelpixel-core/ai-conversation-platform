"""Template canónico para Event Envelope (Envoltorio de Eventos de Integración).

Reglas:
- Pertenece a src/domain/shared/events/.
- Encapsula metadatos estándar de mensajería (id, event_type, correlation_id, causation_id, occurred_at, payload).
- Inmutable o agnóstico a frameworks de transporte (RabbitMQ, Kafka, Redis).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class EventEnvelope:
    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> "EventEnvelope":
        return cls(
            id=uuid4(),
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_at=datetime.now(timezone.utc),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "payload": self.payload,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            correlation_id=(
                UUID(data["correlation_id"])
                if data.get("correlation_id") and isinstance(data["correlation_id"], str)
                else data.get("correlation_id")
            ),
            causation_id=(
                UUID(data["causation_id"])
                if data.get("causation_id") and isinstance(data["causation_id"], str)
                else data.get("causation_id")
            ),
            occurred_at=(
                datetime.fromisoformat(data["occurred_at"])
                if isinstance(data["occurred_at"], str)
                else data["occurred_at"]
            ),
        )
