"""HTTP request dependencies."""

from src.interfaces.http.dependencies.idempotency_dependency import (
    get_optional_idempotency_key,
    get_required_idempotency_key,
)
from src.interfaces.http.dependencies.tenant_dependency import (
    get_current_tenant_id_dep,
    get_optional_tenant_id_dep,
)

__all__ = [
    "get_current_tenant_id_dep",
    "get_optional_idempotency_key",
    "get_optional_tenant_id_dep",
    "get_required_idempotency_key",
]
