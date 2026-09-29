"""ResumeWorkflow command and handler for multi-agent workflows."""

from dataclasses import dataclass
from typing import Any

from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.domain.agents.entities.workflow_instance import WorkflowStatus
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class ResumeWorkflowCommand:
    """Command to resume a paused or approval-gated workflow."""

    tenant_id: str
    workflow_id: str
    resumed_state_updates: dict[str, Any]


@dataclass(frozen=True)
class ResumeWorkflowResult:
    """Result returned after resuming workflow."""

    workflow_id: str
    status: str
    current_node: str
    version: int


class ResumeWorkflowCommandHandler:
    """Handles resumption of paused workflows from persistent state checkpoints."""

    def __init__(
        self,
        checkpoint_repo: WorkflowCheckpointRepositoryPort,
        engine: GraphExecutionEngine,
    ) -> None:
        self._repo = checkpoint_repo
        self._engine = engine

    async def handle(self, command: ResumeWorkflowCommand) -> ResumeWorkflowResult:
        tenant_id = TenantId(command.tenant_id)
        instance = self._repo.get_instance(tenant_id, command.workflow_id)
        if instance is None:
            raise ValueError(f"Workflow '{command.workflow_id}' no encontrado.")

        if instance.status not in (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.RUNNING):
            raise ValueError(f"No se puede reanudar un workflow en estado '{instance.status}'.")

        # Update state with incoming payload and restore running status if suspended
        instance.state_data.update(command.resumed_state_updates)
        if instance.status == WorkflowStatus.WAITING_APPROVAL:
            instance.status = WorkflowStatus.RUNNING

        executed = await self._engine.run_until_completion(instance)
        self._repo.save_instance(executed)

        return ResumeWorkflowResult(
            workflow_id=executed.id,
            status=str(executed.status),
            current_node=executed.current_node,
            version=executed.version,
        )
