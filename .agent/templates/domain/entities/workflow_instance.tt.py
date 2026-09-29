"""Canonical template: WorkflowInstance Aggregate Root."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId


class WorkflowStatus(StrEnum):
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowInstance(AggregateRoot):
    """Aggregate root managing the lifecycle of an executed workflow instance."""

    def __init__(
        self,
        workflow_id: str,
        tenant_id: TenantId,
        name: str,
        current_node: str,
        status: WorkflowStatus = WorkflowStatus.RUNNING,
        state_data: dict[str, Any] | None = None,
        version: int = 1,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__()
        self.id = workflow_id
        self.tenant_id = tenant_id
        self.name = name
        self.current_node = current_node
        self.status = status
        self.state_data: dict[str, Any] = state_data or {}
        self.version = version
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)

    def transition_to(self, next_node: str, updated_state: dict[str, Any]) -> StateSnapshot:
        """Transitions workflow to next node, updates state data and increments version."""
        if self.status != WorkflowStatus.RUNNING:
            raise ValueError(f"No se puede realizar una transición en estado '{self.status}'.")
        self.current_node = next_node
        self.state_data.update(updated_state)
        self.version += 1
        self.updated_at = datetime.now(UTC)
        return StateSnapshot(
            checkpoint_id=f"chk-{self.id}-{self.version}",
            tenant_id=self.tenant_id,
            workflow_id=self.id,
            current_node=self.current_node,
            state_data=dict(self.state_data),
            version=self.version,
            status=self.status,
            created_at=self.updated_at,
        )

    def mark_completed(self) -> None:
        self.status = WorkflowStatus.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_waiting_approval(self) -> None:
        self.status = WorkflowStatus.WAITING_APPROVAL
        self.updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.status = WorkflowStatus.FAILED
        self.updated_at = datetime.now(UTC)
