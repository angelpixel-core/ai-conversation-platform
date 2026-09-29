"""WorkflowDataMapper for converting between domain entities and SQLModel models."""

import json

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import (
    WorkflowCheckpointModel,
    WorkflowInstanceModel,
)


class WorkflowMapper:
    """Translates between DDD aggregates/snapshots and physical SQLModel relational models."""

    @staticmethod
    def to_model_instance(domain: WorkflowInstance) -> WorkflowInstanceModel:
        """Converts domain WorkflowInstance aggregate root to SQLModel physical table model."""
        return WorkflowInstanceModel(
            id=domain.id,
            tenant_id=domain.tenant_id.value,
            name=domain.name,
            status=str(domain.status),
            current_node=domain.current_node,
            state_json=json.dumps(domain.state_data),
            version=domain.version,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    @staticmethod
    def to_domain_instance(model: WorkflowInstanceModel) -> WorkflowInstance:
        """Reconstructs domain WorkflowInstance aggregate root from SQLModel table model."""
        state_data = json.loads(model.state_json) if model.state_json else {}
        return WorkflowInstance(
            workflow_id=model.id,
            tenant_id=TenantId(model.tenant_id),
            name=model.name,
            current_node=model.current_node,
            status=WorkflowStatus(model.status),
            state_data=state_data,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model_checkpoint(domain: StateSnapshot) -> WorkflowCheckpointModel:
        """Converts domain StateSnapshot value object to SQLModel physical checkpoint model."""
        return WorkflowCheckpointModel(
            id=domain.checkpoint_id,
            tenant_id=domain.tenant_id.value,
            workflow_id=domain.workflow_id,
            version=domain.version,
            node_id=domain.current_node,
            state_json=json.dumps(domain.state_data),
            status=domain.status,
            created_at=domain.created_at,
        )

    @staticmethod
    def to_domain_checkpoint(model: WorkflowCheckpointModel) -> StateSnapshot:
        """Reconstructs domain StateSnapshot from SQLModel physical checkpoint model."""
        state_data = json.loads(model.state_json) if model.state_json else {}
        return StateSnapshot(
            checkpoint_id=model.id,
            tenant_id=TenantId(model.tenant_id),
            workflow_id=model.workflow_id,
            current_node=model.node_id,
            state_data=state_data,
            version=model.version,
            status=model.status,
            created_at=model.created_at,
        )
