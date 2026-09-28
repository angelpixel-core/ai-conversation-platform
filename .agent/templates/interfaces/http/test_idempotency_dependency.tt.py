"""Test template canónico para Idempotency Dependency en FastAPI."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from .idempotency_dependency import (
    get_optional_idempotency_key,
    get_required_idempotency_key,
)

app = FastAPI()


@app.get("/test-optional")
async def optional_endpoint(key: str | None = None) -> dict[str, str | None]:
    return {"key": key}


@app.post("/test-required")
async def required_endpoint(key: str) -> dict[str, str]:
    return {"key": key}


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
async def test_get_required_idempotency_key_missing_raises_http_400() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_required_idempotency_key(None)
    assert exc_info.value.status_code == 400
