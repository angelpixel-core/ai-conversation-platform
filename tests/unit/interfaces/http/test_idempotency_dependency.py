"""Unit tests for HTTP Idempotency Dependency."""

import pytest
from fastapi import HTTPException

from src.domain.conversations.exceptions import InvalidUuidFormatError
from src.interfaces.http.dependencies.idempotency_dependency import (
    get_optional_idempotency_key,
    get_required_idempotency_key,
)


@pytest.mark.anyio
async def test_get_optional_idempotency_key_valid() -> None:
    extracted = await get_optional_idempotency_key("valid-key-123")
    assert extracted == "valid-key-123"


@pytest.mark.anyio
async def test_get_optional_idempotency_key_none() -> None:
    extracted = await get_optional_idempotency_key(None)
    assert extracted is None


@pytest.mark.anyio
async def test_get_optional_idempotency_key_invalid_raises_http_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_optional_idempotency_key("invalid key with space")
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_get_optional_x_idempotency_key_valid_uuidv4() -> None:
    valid_uuid4 = "550e8400-e29b-41d4-a716-446655440000"
    extracted = await get_optional_idempotency_key(None, valid_uuid4)
    assert extracted == valid_uuid4


@pytest.mark.anyio
async def test_get_optional_x_idempotency_key_invalid_uuidv4_raises_error() -> None:
    with pytest.raises(InvalidUuidFormatError) as exc_info:
        await get_optional_idempotency_key(None, "not-a-valid-uuidv4")
    assert "not-a-valid-uuidv4" in str(exc_info.value)


@pytest.mark.anyio
async def test_get_required_idempotency_key_valid() -> None:
    extracted = await get_required_idempotency_key("valid-key-456")
    assert extracted == "valid-key-456"


@pytest.mark.anyio
async def test_get_required_idempotency_key_missing_raises_http_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_required_idempotency_key(None)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_get_required_idempotency_key_empty_raises_http_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_required_idempotency_key("")
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_get_required_idempotency_key_invalid_raises_http_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_required_idempotency_key("invalid key with spaces")
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_get_required_x_idempotency_key_valid_uuidv4() -> None:
    valid_uuid4 = "550e8400-e29b-41d4-a716-446655440000"
    extracted = await get_required_idempotency_key(None, valid_uuid4)
    assert extracted == valid_uuid4


@pytest.mark.anyio
async def test_get_required_x_idempotency_key_invalid_uuidv4_raises_error() -> None:
    with pytest.raises(InvalidUuidFormatError):
        await get_required_idempotency_key(None, "12345-not-uuid4")
