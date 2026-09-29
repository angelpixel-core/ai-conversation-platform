"""MssqlWorkflowCheckpointRepository implementing WorkflowCheckpointRepositoryPort."""

from sqlmodel import Session, col, select

from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import (
    WorkflowCheckpointModel,
    WorkflowInstanceModel,
)
from src.infrastructure.persistence.mssql.workflow_mapper import WorkflowMapper


class MssqlWorkflowCheckpointRepository(WorkflowCheckpointRepositoryPort):
    """MSSQL 2022 persistent adapter for workflow instances and immutable checkpoints."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_instance(self, instance: WorkflowInstance) -> None:
        """Persists or updates a workflow instance."""
        model = WorkflowMapper.to_model_instance(instance)
        self._session.merge(model)

    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        """Retrieves a workflow instance under strict tenant isolation."""
        stmt = select(WorkflowInstanceModel).where(
            WorkflowInstanceModel.tenant_id == tenant_id.value,
            WorkflowInstanceModel.id == workflow_id,
        )
        model = self._session.exec(stmt).first()
        if model is None:
            return None
        return WorkflowMapper.to_domain_instance(model)

    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        """Persists an immutable state snapshot."""
        model = WorkflowMapper.to_model_checkpoint(snapshot)
        self._session.merge(model)

    def get_latest_checkpoint(self, tenant_id: TenantId, workflow_id: str) -> StateSnapshot | None:
        """Retrieves the latest state snapshot under tenant isolation."""
        stmt = (
            select(WorkflowCheckpointModel)
            .where(
                WorkflowCheckpointModel.tenant_id == tenant_id.value,
                WorkflowCheckpointModel.workflow_id == workflow_id,
            )
            .order_by(col(WorkflowCheckpointModel.version).desc())
        )
        model = self._session.exec(stmt).first()
        if model is None:
            return None
        return WorkflowMapper.to_domain_checkpoint(model)

    def list_checkpoints(self, tenant_id: TenantId, workflow_id: str) -> list[StateSnapshot]:
        """Lists all historical checkpoints for a given workflow instance ordered by version."""
        stmt = (
            select(WorkflowCheckpointModel)
            .where(
                WorkflowCheckpointModel.tenant_id == tenant_id.value,
                WorkflowCheckpointModel.workflow_id == workflow_id,
            )
            .order_by(col(WorkflowCheckpointModel.version).asc())
        )
        models = self._session.exec(stmt).all()
        return [WorkflowMapper.to_domain_checkpoint(m) for m in models]
