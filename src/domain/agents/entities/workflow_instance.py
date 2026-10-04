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
        self._id = clean_id
        self._tenant_id = tenant_id
        self._name = name.strip() if name else ""
        self._current_node = current_node.strip() if current_node else ""
        self._status = status
        self._state_data: dict[str, Any] = dict(state_data) if state_data else {}
        self._version = version
        self._created_at = created_at or datetime.now(UTC)
        self._updated_at = updated_at or datetime.now(UTC)

    @property
    def id(self) -> str:
        """Unique identifier of the workflow instance."""
        return self._id

    @property
    def tenant_id(self) -> TenantId:
        """Tenant owning this workflow."""
        return self._tenant_id

    @property
    def name(self) -> str:
        """Descriptive name of the workflow execution."""
        return self._name

    @property
    def current_node(self) -> str:
        """Active graph node where execution is currently paused or running."""
        return self._current_node

    @property
    def status(self) -> WorkflowStatus:
        """Operational status of the workflow."""
        return self._status

    @status.setter
    def status(self, new_status: WorkflowStatus) -> None:
        """Sets workflow operational status (supported for backward-compatibility)."""
        self._status = new_status

    @property
    def state_data(self) -> dict[str, Any]:
        """Current state dictionary."""
        return self._state_data

    @property
    def version(self) -> int:
        """Incremental state transition version counter."""
        return self._version

    @property
    def created_at(self) -> datetime:
        """Timestamp of workflow creation."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Timestamp of last transition or state mutation."""
        return self._updated_at

    def resume(self, resumed_state_updates: dict[str, Any] | None = None) -> None:
        """Resumes a workflow suspended awaiting approval."""
        if self._status not in (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.RUNNING):
            raise InvalidGraphTransitionError(
                f"No se puede reanudar un workflow en estado '{self._status}'."
            )
        if resumed_state_updates:
            self._state_data.update(resumed_state_updates)
        self._status = WorkflowStatus.RUNNING
        self._updated_at = datetime.now(UTC)

    def update_state(self, updates: dict[str, Any]) -> None:
        """Updates internal state data dictionary."""
        self._state_data.update(updates)
        self._updated_at = datetime.now(UTC)

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
        if self._status != WorkflowStatus.RUNNING:
            raise InvalidGraphTransitionError(
                f"No se puede realizar una transición en estado '{self._status}'."
            )
        clean_next = next_node.strip() if next_node else ""
        if not clean_next:
            raise ValueError("El next_node no puede estar vacío.")

        self._current_node = clean_next
        self._state_data.update(updated_state)
        self._version += 1
        self._updated_at = datetime.now(UTC)

        checkpoint_id = f"chk-{self._id}-{self._version}"
        snapshot = StateSnapshot(
            checkpoint_id=checkpoint_id,
            tenant_id=self._tenant_id,
            workflow_id=self._id,
            current_node=self._current_node,
            state_data=dict(self._state_data),
            version=self._version,
            status=self._status,
            created_at=self._updated_at,
        )

        self.record_event(
            CheckpointSavedDomainEvent(
                workflow_id=self._id,
                tenant_id=self._tenant_id.value,
                checkpoint_id=checkpoint_id,
                node_id=self._current_node,
                version=self._version,
                occurred_at=self._updated_at,
            )
        )
        return snapshot

    def delegate_subagent(self, from_node: str, to_agent: str, subtask: str) -> None:
        """Records delegation from a coordinator/supervisor to a specialized subagent."""
        self.record_event(
            SubAgentTaskDelegatedDomainEvent(
                workflow_id=self._id,
                tenant_id=self._tenant_id.value,
                from_node=from_node,
                to_agent=to_agent,
                subtask=subtask,
                occurred_at=datetime.now(UTC),
            )
        )

    def mark_waiting_approval(self, approval_id: str, tool_name: str) -> None:
        """Suspends workflow awaiting human authorization (Slice 8 HITL integration)."""
        self._status = WorkflowStatus.WAITING_APPROVAL
        self._updated_at = datetime.now(UTC)
        self.record_event(
            WorkflowApprovalRequiredDomainEvent(
                workflow_id=self._id,
                tenant_id=self._tenant_id.value,
                approval_id=approval_id,
                tool_name=tool_name,
                occurred_at=self._updated_at,
            )
        )

    def mark_completed(self, final_output: str | None = None) -> None:
        """Marks the workflow execution as successfully finished."""
        self._status = WorkflowStatus.COMPLETED
        if final_output is not None:
            self._state_data["final_output"] = final_output
        self._updated_at = datetime.now(UTC)
        self.record_event(
            WorkflowCompletedDomainEvent(
                workflow_id=self._id,
                tenant_id=self._tenant_id.value,
                final_node=self._current_node,
                occurred_at=self._updated_at,
            )
        )

    def mark_failed(self, reason: str | None = None) -> None:
        """Marks the workflow execution as failed."""
        self._status = WorkflowStatus.FAILED
        if reason:
            self._state_data["error"] = reason
        self._updated_at = datetime.now(UTC)
