"""HTTP Idempotency Header Dependency for FastAPI.

Extracts and validates the 'X-Idempotency-Key' (RFC-33 UUIDv4) or legacy 'Idempotency-Key' header.
"""

from typing import Annotated

from fastapi import Header, HTTPException, status

from src.domain.conversations.value_objects.idempotency_key import IdempotencyKey


async def get_optional_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
) -> str | None:
    """Extract and validate the optional idempotency key from HTTP headers.

    Args:
        idempotency_key: Legacy 'Idempotency-Key' header value.
        x_idempotency_key: Canonical RFC-33 'X-Idempotency-Key' (UUIDv4) header value.

    Returns:
        Normalized idempotency key string if provided, otherwise None.
    """
    if x_idempotency_key is not None:
        vo = IdempotencyKey.from_uuid_v4(x_idempotency_key)
        return vo.value

    if idempotency_key is None:
        return None

    try:
        vo = IdempotencyKey(idempotency_key)
        return vo.value
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encabezado 'Idempotency-Key' inválido: {exc}",
        ) from exc


async def get_required_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
) -> str:
    """Extract and validate the required idempotency key from HTTP headers."""
    if x_idempotency_key is not None:
        vo = IdempotencyKey.from_uuid_v4(x_idempotency_key)
        return vo.value

    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El encabezado 'Idempotency-Key' es obligatorio para esta operación.",
        )

    try:
        vo = IdempotencyKey(idempotency_key)
        return vo.value
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Encabezado 'Idempotency-Key' inválido: {exc}",
        ) from exc
