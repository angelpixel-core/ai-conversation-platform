"""Unit tests for WorkflowMapper."""

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.models import (
    WorkflowCheckpointModel,
    WorkflowInstanceModel,
)
from src.infrastructure.persistence.mssql.workflow_mapper import WorkflowMapper


def test_mapper_workflow_instance_roundtrip() -> None:
    tenant_id = TenantId("corp-acme")
    domain_instance = WorkflowInstance(
        workflow_id="wf-99",
        tenant_id=tenant_id,
        name="Contract Review",
        current_node="researcher",
        status=WorkflowStatus.RUNNING,
        state_data={"goal": "audit", "sources": ["doc.pdf"]},
        version=2,
    )

    model = WorkflowMapper.to_model_instance(domain_instance)
    assert isinstance(model, WorkflowInstanceModel)
    assert model.id == "wf-99"
    assert model.tenant_id == "corp-acme"
    assert model.status == "RUNNING"
    assert model.version == 2
    assert "doc.pdf" in model.state_json

    restored = WorkflowMapper.to_domain_instance(model)
    assert isinstance(restored, WorkflowInstance)
    assert restored.id == "wf-99"
    assert restored.tenant_id == tenant_id
    assert restored.status == WorkflowStatus.RUNNING
    assert restored.current_node == "researcher"
    assert restored.version == 2
    assert restored.state_data["sources"] == ["doc.pdf"]


def test_mapper_state_snapshot_roundtrip() -> None:
    tenant_id = TenantId("corp-acme")
    domain_snapshot = StateSnapshot(
        checkpoint_id="chk-99-2",
        tenant_id=tenant_id,
        workflow_id="wf-99",
        current_node="researcher",
        state_data={"findings": ["clause_1"]},
        version=2,
        status="RUNNING",
    )

    model = WorkflowMapper.to_model_checkpoint(domain_snapshot)
    assert isinstance(model, WorkflowCheckpointModel)
    assert model.id == "chk-99-2"
    assert model.tenant_id == "corp-acme"
    assert model.workflow_id == "wf-99"
    assert model.version == 2
    assert model.node_id == "researcher"
    assert "clause_1" in model.state_json

    restored = WorkflowMapper.to_domain_checkpoint(model)
    assert isinstance(restored, StateSnapshot)
    assert restored.checkpoint_id == "chk-99-2"
    assert restored.tenant_id == tenant_id
    assert restored.workflow_id == "wf-99"
    assert restored.version == 2
    assert restored.state_data["findings"] == ["clause_1"]
