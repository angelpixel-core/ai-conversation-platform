"""StartWorkflow command and handler for multi-agent workflows."""

from dataclasses import dataclass
from typing import Any

from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class StartWorkflowCommand:
    """Command to initialize and execute a multi-agent workflow."""

    tenant_id: str
    workflow_id: str
    name: str
    initial_state: dict[str, Any] | None = None


@dataclass(frozen=True)
class StartWorkflowResult:
    """Result returned after running workflow."""

    workflow_id: str
    status: str
    current_node: str
    version: int


class StartWorkflowCommandHandler:
    """Handles initialization and initial execution of a workflow."""

    def __init__(
        self,
        checkpoint_repo: WorkflowCheckpointRepositoryPort,
        engine: GraphExecutionEngine,
    ) -> None:
        self._repo = checkpoint_repo
        self._engine = engine

    async def handle(self, command: StartWorkflowCommand) -> StartWorkflowResult:
        tenant_id = TenantId(command.tenant_id)
        entry_node = self._engine.graph.entry_node

        instance = WorkflowInstance.create(
            workflow_id=command.workflow_id,
            tenant_id=tenant_id,
            name=command.name,
            initial_node=entry_node,
            initial_state=command.initial_state,
        )

        initial_snapshot = StateSnapshot(
            checkpoint_id=f"chk-{instance.id}-1",
            tenant_id=instance.tenant_id,
            workflow_id=instance.id,
            current_node=instance.current_node,
            state_data=dict(instance.state_data),
            version=1,
            status=instance.status,
            created_at=instance.created_at,
        )

        self._repo.save_instance(instance)
        self._repo.save_checkpoint(initial_snapshot)

        executed_instance = await self._engine.run_until_completion(instance)
        self._repo.save_instance(executed_instance)

        return StartWorkflowResult(
            workflow_id=executed_instance.id,
            status=str(executed_instance.status),
            current_node=executed_instance.current_node,
            version=executed_instance.version,
        )


__all__ = [
    "StartWorkflowCommand",
    "StartWorkflowCommandHandler",
    "StartWorkflowResult",
]
