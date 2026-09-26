"""Template canónico para Pruebas Unitarias de EventEnvelope.

Reglas:
- Verifica creación con valores por defecto y timestamp UTC.
- Verifica serialización to_dict y deserialización from_dict bidireccional.
"""

from uuid import uuid4
from datetime import datetime, timezone
import pytest

from .event_envelope.tt import EventEnvelope  # type: ignore[import-not-found]


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
    assert envelope.occurred_at.tzinfo == timezone.utc


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
    assert restored.occurred_at == envelope.occurred_at
