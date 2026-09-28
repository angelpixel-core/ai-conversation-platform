"""Template canónico para Idempotency Dependency en FastAPI.

Reglas:
- Pertenece a src/interfaces/http/dependencies/.
- Extrae y valida el header Idempotency-Key en endpoints HTTP.
- Lanza HTTPException(status_code=400) si la clave es inválida o malformada.
"""

from typing import Annotated

from fastapi import Header, HTTPException, status

from src.domain.conversations.value_objects.idempotency_key import IdempotencyKey


async def get_optional_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    """Extrae y valida la clave de idempotencia opcional del header HTTP."""
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
    """Extrae y valida la clave de idempotencia requerida del header HTTP."""
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
