"""Template canónico para Pruebas Unitarias de EventEnvelope.

Reglas:
- Verifica creación con valores por defecto y timestamp UTC en occurred_on.
- Verifica serialización to_dict y deserialización from_dict bidireccional.
- Verifica creación a partir de eventos de dominio.
"""

from uuid import uuid4
from datetime import UTC, datetime
from dataclasses import dataclass
import pytest

from .event_envelope.tt import EventEnvelope  # type: ignore[import-not-found]


@dataclass(frozen=True)
class SampleDomainEvent:
    event_id: uuid4
    item_id: str
    occurred_at: datetime


def test_event_envelope_creation() -> None:
    correlation_id = uuid4()
    envelope = EventEnvelope.create(
        event_type="test.event.created",
        payload={"foo": "bar"},
        correlation_id=correlation_id,
    )

    assert envelope.id is not None
    assert envelope.event_type == "test.event.created"
    assert envelope.payload == {"foo": "bar"}
    assert envelope.correlation_id == correlation_id
    assert envelope.occurred_on.tzinfo == UTC
    assert envelope.occurred_at == envelope.occurred_on


def test_event_envelope_serialization_roundtrip() -> None:
    correlation_id = uuid4()
    causation_id = uuid4()
    envelope = EventEnvelope.create(
        event_type="conversation.message.appended",
        payload={"message_id": "123", "content": "hello"},
        correlation_id=correlation_id,
        causation_id=causation_id,
    )

    data = envelope.to_dict()
    restored = EventEnvelope.from_dict(data)

    assert restored.id == envelope.id
    assert restored.event_type == envelope.event_type
    assert restored.payload == envelope.payload
    assert restored.correlation_id == envelope.correlation_id
    assert restored.causation_id == envelope.causation_id
    assert restored.occurred_on == envelope.occurred_on


def test_event_envelope_from_sample_domain_event() -> None:
    event_id = uuid4()
    now = datetime.now(UTC)
    domain_event = SampleDomainEvent(
        event_id=event_id,
        item_id="item-456",
        occurred_at=now,
    )
    correlation_id = uuid4()

    envelope = EventEnvelope.from_domain_event(
        event=domain_event,
        correlation_id=correlation_id,
    )

    assert envelope.id == event_id
    assert envelope.event_type == "sample"
    assert envelope.payload == {"item_id": "item-456"}
    assert envelope.correlation_id == correlation_id
    assert envelope.occurred_on == now
