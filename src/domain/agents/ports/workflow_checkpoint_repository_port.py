"""WorkflowCheckpointRepositoryPort Driven Port."""

from abc import ABC, abstractmethod

from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


class WorkflowCheckpointRepositoryPort(ABC):
    """Port for transactional persistence and retrieval of workflow instances and checkpoints."""

    @abstractmethod
    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        """Persists an immutable state snapshot."""
        pass

    @abstractmethod
    def get_latest_checkpoint(self, tenant_id: TenantId, workflow_id: str) -> StateSnapshot | None:
        """Retrieves latest state snapshot for a workflow instance under tenant isolation."""
        pass

    @abstractmethod
    def list_checkpoints(self, tenant_id: TenantId, workflow_id: str) -> list[StateSnapshot]:
        """Lists all historical checkpoints for a given workflow instance ordered by version."""
        pass

    @abstractmethod
    def save_instance(self, instance: WorkflowInstance) -> None:
        """Persists or updates a workflow instance."""
        pass

    @abstractmethod
    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        """Retrieves a workflow instance under tenant isolation."""
        pass
