"""Template canónico para Event Envelope (Envoltorio de Eventos de Integración).

Reglas:
- Pertenece a src/domain/shared/events/.
- Encapsula metadatos estándar de mensajería (id, event_type, correlation_id, causation_id, occurred_on, payload).
- Inmutable o agnóstico a frameworks de transporte (RabbitMQ, Kafka, Redis).
"""

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
import re
from typing import Any
from uuid import UUID, uuid4


def _to_snake_case(name: str) -> str:
    """Convert PascalCase name to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


@dataclass(frozen=True)
class EventEnvelope:
    """Standardized event envelope encapsulating integration metadata and payload."""

    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    occurred_on: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def occurred_at(self) -> datetime:
        """Alias for occurred_on for consistency with DomainEvent interface."""
        return self.occurred_on

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
        occurred_on: datetime | None = None,
        envelope_id: UUID | None = None,
    ) -> "EventEnvelope":
        """Factory method to construct an EventEnvelope."""
        return cls(
            id=envelope_id or uuid4(),
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_on=occurred_on or datetime.now(UTC),
        )

    @classmethod
    def from_domain_event(
        cls,
        event: Any,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> "EventEnvelope":
        """Construct an EventEnvelope from a DomainEvent aggregate."""
        raw_name = type(event).__name__
        if raw_name.endswith("DomainEvent"):
            raw_name = raw_name[: -len("DomainEvent")]
        event_type = _to_snake_case(raw_name)

        payload: dict[str, Any] = {}
        if is_dataclass(event) and not isinstance(event, type):
            event_dict = asdict(event)
            for k, v in event_dict.items():
                if k in ("event_id", "occurred_at"):
                    continue
                if isinstance(v, UUID):
                    payload[k] = str(v)
                elif isinstance(v, datetime):
                    payload[k] = v.isoformat()
                else:
                    payload[k] = v

        event_id = getattr(event, "event_id", None)
        occurred_at = getattr(event, "occurred_at", None)

        return cls(
            id=event_id if isinstance(event_id, UUID) else uuid4(),
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_on=occurred_at if isinstance(occurred_at, datetime) else datetime.now(UTC),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize envelope to JSON-serializable dictionary."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "payload": self.payload,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "occurred_on": self.occurred_on.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        """Deserialize dictionary into an EventEnvelope instance."""
        raw_id = data.get("id")
        envelope_id = UUID(raw_id) if isinstance(raw_id, str) else (raw_id or uuid4())

        raw_corr = data.get("correlation_id")
        correlation_id = UUID(raw_corr) if isinstance(raw_corr, str) else raw_corr

        raw_caus = data.get("causation_id")
        causation_id = UUID(raw_caus) if isinstance(raw_caus, str) else raw_caus

        raw_occurred = data.get("occurred_on") or data.get("occurred_at")
        if isinstance(raw_occurred, str):
            occurred_on = datetime.fromisoformat(raw_occurred)
        elif isinstance(raw_occurred, datetime):
            occurred_on = raw_occurred
        else:
            occurred_on = datetime.now(UTC)

        return cls(
            id=envelope_id,
            event_type=data.get("event_type", ""),
            payload=data.get("payload", {}),
            correlation_id=correlation_id,
            causation_id=causation_id,
            occurred_on=occurred_on,
        )
