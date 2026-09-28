"""Unit tests for IdempotencyKey Value Object."""

import pytest

from src.domain.conversations.value_objects.idempotency_key import IdempotencyKey


def test_idempotency_key_valid_creation() -> None:
    key = IdempotencyKey("req-12345-abc")
    assert key.value == "req-12345-abc"
    assert str(key) == "req-12345-abc"


def test_idempotency_key_strips_whitespace() -> None:
    key = IdempotencyKey("  token_abc-123  ")
    assert key.value == "token_abc-123"


def test_idempotency_key_generate_uuid4() -> None:
    key = IdempotencyKey.generate()
    assert len(key.value) == 36
    assert "-" in key.value


def test_idempotency_key_equality_by_value() -> None:
    key1 = IdempotencyKey("same-key-1")
    key2 = IdempotencyKey("same-key-1")
    assert key1 == key2
    assert hash(key1) == hash(key2)


def test_idempotency_key_immutability() -> None:
    key = IdempotencyKey("static-key-1")
    with pytest.raises(AttributeError):
        key.value = "mutated-key"  # type: ignore[misc]


def test_idempotency_key_empty_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no puede estar vacía"):
        IdempotencyKey("")

    with pytest.raises(ValueError, match="no puede estar vacía"):
        IdempotencyKey("   ")


def test_idempotency_key_too_long_raises_value_error() -> None:
    with pytest.raises(ValueError, match="no puede exceder 128 caracteres"):
        IdempotencyKey("a" * 129)


def test_idempotency_key_invalid_characters_raises_value_error() -> None:
    with pytest.raises(ValueError, match="caracteres inválidos"):
        IdempotencyKey("key with spaces!")

    with pytest.raises(ValueError, match="caracteres inválidos"):
        IdempotencyKey("key$with%symbols*")
