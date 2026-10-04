"""In-memory Workflow Checkpoint repository adapter for fast unit tests."""

from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


class InMemoryWorkflowCheckpointRepositoryAdapter(WorkflowCheckpointRepositoryPort):
    """Fast in-memory dictionary-backed repository for workflows and state checkpoints."""

    def __init__(self) -> None:
        self._instances: dict[tuple[str, str], WorkflowInstance] = {}
        self._checkpoints: dict[tuple[str, str], list[StateSnapshot]] = {}

    def save_instance(self, instance: WorkflowInstance) -> None:
        """Persists or updates a workflow instance."""
        self._instances[(str(instance.tenant_id), instance.id)] = instance

    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        """Retrieves a workflow instance under tenant isolation."""
        return self._instances.get((str(tenant_id), workflow_id))

    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        """Persists an immutable state snapshot."""
        key = (str(snapshot.tenant_id), snapshot.workflow_id)
        if key not in self._checkpoints:
            self._checkpoints[key] = []
        self._checkpoints[key].append(snapshot)

    def get_latest_checkpoint(self, tenant_id: TenantId, workflow_id: str) -> StateSnapshot | None:
        """Retrieves latest state snapshot for a workflow instance under tenant isolation."""
        key = (str(tenant_id), workflow_id)
        snaps = self._checkpoints.get(key, [])
        if not snaps:
            return None
        return max(snaps, key=lambda s: s.version)

    def list_checkpoints(self, tenant_id: TenantId, workflow_id: str) -> list[StateSnapshot]:
        """Lists all historical checkpoints for a given workflow instance ordered by version."""
        key = (str(tenant_id), workflow_id)
        snaps = self._checkpoints.get(key, [])
        return sorted(snaps, key=lambda s: s.version)


__all__ = ["InMemoryWorkflowCheckpointRepositoryAdapter"]
