"""MssqlWorkflowCheckpointRepository implementing WorkflowCheckpointRepositoryPort."""

from collections.abc import Callable, Generator
from contextlib import contextmanager

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


class MssqlWorkflowCheckpointRepositoryAdapter(WorkflowCheckpointRepositoryPort):
    """MSSQL 2022 persistent adapter for workflow instances and immutable checkpoints."""

    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        if callable(self._session_or_factory):
            with self._session_or_factory() as session:
                yield session
        else:
            yield self._session_or_factory

    def save_instance(self, instance: WorkflowInstance) -> None:
        """Persists or updates a workflow instance."""
        model = WorkflowMapper.to_model_instance(instance)
        with self._get_session() as session:
            session.merge(model)
            session.commit()

    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        """Retrieves a workflow instance under strict tenant isolation."""
        stmt = select(WorkflowInstanceModel).where(
            WorkflowInstanceModel.tenant_id == tenant_id.value,
            WorkflowInstanceModel.id == workflow_id,
        )
        with self._get_session() as session:
            model = session.exec(stmt).first()
            if model is None:
                return None
            return WorkflowMapper.to_domain_instance(model)

    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        """Persists an immutable state snapshot."""
        model = WorkflowMapper.to_model_checkpoint(snapshot)
        with self._get_session() as session:
            session.merge(model)
            session.commit()

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
        with self._get_session() as session:
            model = session.exec(stmt).first()
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
        with self._get_session() as session:
            models = session.exec(stmt).all()
            return [WorkflowMapper.to_domain_checkpoint(m) for m in models]


__all__ = ["MssqlWorkflowCheckpointRepositoryAdapter"]
