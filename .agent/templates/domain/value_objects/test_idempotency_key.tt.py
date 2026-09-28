"""Test template canónico para IdempotencyKey Value Object."""

import pytest
from .idempotency_key import IdempotencyKey


def test_idempotency_key_valid_creation() -> None:
    key = IdempotencyKey("req-12345-abc")
    assert key.value == "req-12345-abc"
    assert str(key) == "req-12345-abc"


def test_idempotency_key_generate_uuid4() -> None:
    key = IdempotencyKey.generate()
    assert len(key.value) == 36
    assert "-" in key.value


def test_idempotency_key_immutability() -> None:
    key = IdempotencyKey("static-key-1")
    with pytest.raises(AttributeError):
        key.value = "mutated-key"  # type: ignore[misc]


def test_idempotency_key_empty_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede estar vacía"):
        IdempotencyKey("   ")


def test_idempotency_key_too_long_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede exceder 128 caracteres"):
        IdempotencyKey("a" * 129)


def test_idempotency_key_invalid_characters_raises_error() -> None:
    with pytest.raises(ValueError, match="caracteres inválidos"):
        IdempotencyKey("key with spaces!")
