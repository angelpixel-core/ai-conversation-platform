"""Test template canónico para AuditLogRecord Entity."""

import uuid
import pytest

from .audit_log_record import AuditLogRecord


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
    assert rec.tokens_consumed == 55
    assert rec.occurred_at.tzinfo is not None


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
    with pytest.raises(ValueError, match="no puede estar vacío"):
        AuditLogRecord.create(
            event_name="",
            actor_id="u-1",
            resource_type="conv",
            resource_id="c-1",
            action="call",
        )
