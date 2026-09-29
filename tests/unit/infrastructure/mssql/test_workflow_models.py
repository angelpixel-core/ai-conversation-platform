"""Unit tests for WorkflowInstanceModel and WorkflowCheckpointModel."""

from src.infrastructure.persistence.mssql.models import (
    WorkflowCheckpointModel,
    WorkflowInstanceModel,
)


def test_workflow_instance_model_instantiation() -> None:
    model = WorkflowInstanceModel(
        id="wf-101",
        tenant_id="corp-acme",
        name="Contract Review",
        status="RUNNING",
        current_node="supervisor",
        state_json='{"goal": "review"}',
        version=1,
    )
    assert model.id == "wf-101"
    assert model.tenant_id == "corp-acme"
    assert model.name == "Contract Review"
    assert model.status == "RUNNING"
    assert model.current_node == "supervisor"
    assert model.version == 1


def test_workflow_checkpoint_model_instantiation() -> None:
    model = WorkflowCheckpointModel(
        id="chk-101-1",
        tenant_id="corp-acme",
        workflow_id="wf-101",
        version=1,
        node_id="supervisor",
        state_json='{"goal": "review", "step": 1}',
        status="RUNNING",
    )
    assert model.id == "chk-101-1"
    assert model.tenant_id == "corp-acme"
    assert model.workflow_id == "wf-101"
    assert model.version == 1
    assert model.node_id == "supervisor"
