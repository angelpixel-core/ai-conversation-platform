"""Template canónico para TenantContext en la Capa de Aplicación.

Reglas:
- Pertenece a Application (src/application/shared/tenancy/).
- Utiliza contextvars.ContextVar para propagación transparente compatible con AnyIO.
- Provee context manager sincrónico y asincrónico para aislar el contexto por request/task.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
import contextvars
from typing import Optional, Union

# ContextVar aislado para el identificador de inquilino activo
_TENANT_ID_CTX: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def get_current_tenant_id() -> Optional[str]:
    """Obtiene el tenant_id activo en el contexto de ejecución actual."""
    return _TENANT_ID_CTX.get()


def set_current_tenant_id(tenant_id: Union[str, None]) -> contextvars.Token[Optional[str]]:
    """Establece manualmente el tenant_id activo y retorna un token para reseteo."""
    cleaned = tenant_id.strip() if tenant_id else None
    return _TENANT_ID_CTX.set(cleaned)


def reset_current_tenant_id(token: contextvars.Token[Optional[str]]) -> None:
    """Restaura el estado previo del contexto de tenant."""
    _TENANT_ID_CTX.reset(token)


@contextmanager
def tenant_context(tenant_id: Union[str, None]) -> Iterator[Optional[str]]:
    """Context manager sincrónico para delimitar el ámbito de un tenant."""
    token = set_current_tenant_id(tenant_id)
    try:
        yield get_current_tenant_id()
    finally:
        reset_current_tenant_id(token)


@asynccontextmanager
async def async_tenant_context(tenant_id: Union[str, None]) -> AsyncIterator[Optional[str]]:
    """Context manager asincrónico compatible con AnyIO para delimitar el ámbito de un tenant."""
    token = set_current_tenant_id(tenant_id)
    try:
        yield get_current_tenant_id()
    finally:
        reset_current_tenant_id(token)
