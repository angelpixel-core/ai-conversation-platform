"""Unit tests for AuditLogRecord Entity (DDD)."""

import uuid
from datetime import UTC, datetime

import pytest

from src.domain.audit.audit_log_entity import AuditLogRecord


def test_audit_log_record_creation() -> None:
    rec = AuditLogRecord.create(
        event_name="llm_tokens_consumed",
        actor_id="user-456",
        resource_type="conversation",
        resource_id="conv-789",
        action="chat_completion",
        payload={"model": "gpt-4o", "prompt_tokens": 15, "completion_tokens": 40},
        tokens_consumed=55,
    )

    assert isinstance(rec.id, uuid.UUID)
    assert rec.event_name == "llm_tokens_consumed"
    assert rec.actor_id == "user-456"
    assert rec.resource_type == "conversation"
    assert rec.resource_id == "conv-789"
    assert rec.action == "chat_completion"
    assert rec.tokens_consumed == 55
    assert rec.payload["model"] == "gpt-4o"
    assert rec.occurred_at.tzinfo == UTC


def test_audit_log_record_immutability() -> None:
    rec = AuditLogRecord.create(
        event_name="login",
        actor_id="user-1",
        resource_type="auth",
        resource_id="sess-1",
        action="login",
    )
    with pytest.raises(AttributeError):
        rec.tokens_consumed = 100  # type: ignore[misc]


def test_audit_log_record_negative_tokens_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        AuditLogRecord.create(
            event_name="llm",
            actor_id="u-1",
            resource_type="conv",
            resource_id="c-1",
            action="call",
            tokens_consumed=-1,
        )


def test_audit_log_record_empty_fields_raises_error() -> None:
    with pytest.raises(ValueError, match="nombre del evento de auditoría no puede estar vacío"):
        AuditLogRecord.create(
            event_name="",
            actor_id="u-1",
            resource_type="conv",
            resource_id="c-1",
            action="call",
        )

    with pytest.raises(ValueError, match="identificador del actor no puede estar vacío"):
        AuditLogRecord.create(
            event_name="event",
            actor_id="   ",
            resource_type="conv",
            resource_id="c-1",
            action="call",
        )

    with pytest.raises(ValueError, match="tipo de recurso no puede estar vacío"):
        AuditLogRecord.create(
            event_name="event",
            actor_id="u-1",
            resource_type="",
            resource_id="c-1",
            action="call",
        )

    with pytest.raises(ValueError, match="ID del recurso no puede estar vacío"):
        AuditLogRecord.create(
            event_name="event",
            actor_id="u-1",
            resource_type="conv",
            resource_id="",
            action="call",
        )

    with pytest.raises(ValueError, match="acción auditada no puede estar vacía"):
        AuditLogRecord.create(
            event_name="event",
            actor_id="u-1",
            resource_type="conv",
            resource_id="c-1",
            action=" ",
        )


def test_audit_log_record_custom_id_and_naive_datetime() -> None:
    custom_id = uuid.uuid4()
    naive_dt = datetime(2026, 9, 27, 12, 0, 0)
    rec = AuditLogRecord(
        id=custom_id,
        event_name="custom_event",
        actor_id="admin",
        resource_type="system",
        resource_id="sys-1",
        action="update",
        payload={"key": "val"},
        tokens_consumed=0,
        occurred_at=naive_dt,
    )
    assert rec.id == custom_id
    assert rec.occurred_at.tzinfo == UTC
