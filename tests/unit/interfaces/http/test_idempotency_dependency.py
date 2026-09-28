"""Unit tests for HTTP Idempotency Dependency."""

import pytest
from fastapi import HTTPException

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
