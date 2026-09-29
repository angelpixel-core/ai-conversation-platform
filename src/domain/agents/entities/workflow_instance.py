"""WorkflowInstance Aggregate Root."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.domain.agents.events.workflow_events import (
    CheckpointSavedDomainEvent,
    SubAgentTaskDelegatedDomainEvent,
    WorkflowApprovalRequiredDomainEvent,
    WorkflowCompletedDomainEvent,
    WorkflowStartedDomainEvent,
)
from src.domain.agents.exceptions import InvalidGraphTransitionError
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.shared.aggregate_root import AggregateRoot
from src.domain.tenants.value_objects.tenant_id import TenantId


class WorkflowStatus(StrEnum):
    """Execution status of a workflow instance."""

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
        clean_id = workflow_id.strip() if workflow_id else ""
        if not clean_id:
            raise ValueError("El workflow_id no puede estar vacío.")
        self.id = clean_id
        self.tenant_id = tenant_id
        self.name = name.strip() if name else ""
        self.current_node = current_node.strip() if current_node else ""
        self.status = status
        self.state_data: dict[str, Any] = dict(state_data) if state_data else {}
        self.version = version
        self.created_at = created_at or datetime.now(UTC)
        self.updated_at = updated_at or datetime.now(UTC)

    @classmethod
    def create(
        cls,
        workflow_id: str,
        tenant_id: TenantId,
        name: str,
        initial_node: str,
        initial_state: dict[str, Any] | None = None,
    ) -> "WorkflowInstance":
        """Factory method to initialize and record the start of a workflow instance."""
        instance = cls(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            name=name,
            current_node=initial_node,
            status=WorkflowStatus.RUNNING,
            state_data=initial_state,
            version=1,
        )
        instance.record_event(
            WorkflowStartedDomainEvent(
                workflow_id=instance.id,
                tenant_id=tenant_id.value,
                name=instance.name,
                initial_node=initial_node,
                occurred_at=instance.created_at,
            )
        )
        return instance

    def transition_to(self, next_node: str, updated_state: dict[str, Any]) -> StateSnapshot:
        """Transitions workflow to next node, updates state data and increments version."""
        if self.status != WorkflowStatus.RUNNING:
            raise InvalidGraphTransitionError(
                f"No se puede realizar una transición en estado '{self.status}'."
            )
        clean_next = next_node.strip() if next_node else ""
        if not clean_next:
            raise ValueError("El next_node no puede estar vacío.")

        self.current_node = clean_next
        self.state_data.update(updated_state)
        self.version += 1
        self.updated_at = datetime.now(UTC)

        checkpoint_id = f"chk-{self.id}-{self.version}"
        snapshot = StateSnapshot(
            checkpoint_id=checkpoint_id,
            tenant_id=self.tenant_id,
            workflow_id=self.id,
            current_node=self.current_node,
            state_data=dict(self.state_data),
            version=self.version,
            status=self.status,
            created_at=self.updated_at,
        )

        self.record_event(
            CheckpointSavedDomainEvent(
                workflow_id=self.id,
                tenant_id=self.tenant_id.value,
                checkpoint_id=checkpoint_id,
                node_id=self.current_node,
                version=self.version,
                occurred_at=self.updated_at,
            )
        )
        return snapshot

    def delegate_subagent(self, from_node: str, to_agent: str, subtask: str) -> None:
        """Records delegation from a coordinator/supervisor to a specialized subagent."""
        self.record_event(
            SubAgentTaskDelegatedDomainEvent(
                workflow_id=self.id,
                tenant_id=self.tenant_id.value,
                from_node=from_node,
                to_agent=to_agent,
                subtask=subtask,
                occurred_at=datetime.now(UTC),
            )
        )

    def mark_waiting_approval(self, approval_id: str, tool_name: str) -> None:
        """Suspends workflow awaiting human authorization (Slice 8 HITL integration)."""
        self.status = WorkflowStatus.WAITING_APPROVAL
        self.updated_at = datetime.now(UTC)
        self.record_event(
            WorkflowApprovalRequiredDomainEvent(
                workflow_id=self.id,
                tenant_id=self.tenant_id.value,
                approval_id=approval_id,
                tool_name=tool_name,
                occurred_at=self.updated_at,
            )
        )

    def mark_completed(self, final_output: str | None = None) -> None:
        """Marks the workflow execution as successfully finished."""
        self.status = WorkflowStatus.COMPLETED
        if final_output is not None:
            self.state_data["final_output"] = final_output
        self.updated_at = datetime.now(UTC)
        self.record_event(
            WorkflowCompletedDomainEvent(
                workflow_id=self.id,
                tenant_id=self.tenant_id.value,
                final_node=self.current_node,
                occurred_at=self.updated_at,
            )
        )

    def mark_failed(self, reason: str | None = None) -> None:
        """Marks the workflow execution as failed."""
        self.status = WorkflowStatus.FAILED
        if reason:
            self.state_data["error"] = reason
        self.updated_at = datetime.now(UTC)
