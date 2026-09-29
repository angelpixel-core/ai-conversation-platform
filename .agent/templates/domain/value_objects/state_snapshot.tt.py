"""Canonical template: StateSnapshot Value Object."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class StateSnapshot:
    """Immutable state snapshot captured at a specific point in workflow execution."""

    checkpoint_id: str
    tenant_id: TenantId
    workflow_id: str
    current_node: str
    state_data: dict[str, Any]
    version: int
    status: str = "RUNNING"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.checkpoint_id.strip():
            raise ValueError("El checkpoint_id no puede estar vacío.")
        if not self.workflow_id.strip():
            raise ValueError("El workflow_id no puede estar vacío.")
        if not self.current_node.strip():
            raise ValueError("El current_node no puede estar vacío.")
        if not isinstance(self.state_data, dict):
            raise ValueError("Los datos del estado deben ser un diccionario.")
        if self.version < 1:
            raise ValueError("La versión del checkpoint debe ser mayor o igual a 1.")
