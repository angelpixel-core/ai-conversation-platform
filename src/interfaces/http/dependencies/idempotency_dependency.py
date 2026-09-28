"""HTTP Idempotency Header Dependency for FastAPI.

Extracts and validates the 'Idempotency-Key' header on inbound requests.
"""

from typing import Annotated

from fastapi import Header, HTTPException, status

from src.domain.conversations.value_objects.idempotency_key import IdempotencyKey


async def get_optional_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    """Extract and validate the optional idempotency key from the HTTP header."""
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
) -> str:
    """Extract and validate the required idempotency key from the HTTP header."""
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
