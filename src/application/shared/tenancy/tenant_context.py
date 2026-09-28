"""Context propagation service for multi-tenant execution contexts."""

import contextvars
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

_TENANT_ID_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def get_current_tenant_id() -> str | None:
    """Retrieve the active tenant ID from the execution context."""
    return _TENANT_ID_CTX.get()


def set_current_tenant_id(tenant_id: str | None) -> contextvars.Token[str | None]:
    """Set the active tenant ID and return a reset token."""
    cleaned = tenant_id.strip() if tenant_id else None
    return _TENANT_ID_CTX.set(cleaned)


def reset_current_tenant_id(token: contextvars.Token[str | None]) -> None:
    """Restore the previous tenant context state."""
    _TENANT_ID_CTX.reset(token)


@contextmanager
def tenant_context(tenant_id: str | None) -> Iterator[str | None]:
    """Synchronous context manager for tenant scoping."""
    token = set_current_tenant_id(tenant_id)
    try:
        yield get_current_tenant_id()
    finally:
        reset_current_tenant_id(token)


@asynccontextmanager
async def async_tenant_context(tenant_id: str | None) -> AsyncIterator[str | None]:
    """Asynchronous context manager for tenant scoping compatible with AnyIO."""
    token = set_current_tenant_id(tenant_id)
    try:
        yield get_current_tenant_id()
    finally:
        reset_current_tenant_id(token)
