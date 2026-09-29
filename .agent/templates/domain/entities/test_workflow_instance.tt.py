"""Canonical test template: WorkflowInstance Aggregate Root."""

import pytest

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_workflow_instance_creation() -> None:
    instance = WorkflowInstance(
        workflow_id="wf-100",
        tenant_id=TenantId("tenant-alpha"),
        name="Contract Review",
        current_node="supervisor",
        state_data={"goal": "review"},
    )
    assert instance.id == "wf-100"
    assert instance.status == WorkflowStatus.RUNNING
    assert instance.version == 1
    assert instance.current_node == "supervisor"


def test_workflow_instance_transition_success() -> None:
    instance = WorkflowInstance(
        workflow_id="wf-100",
        tenant_id=TenantId("tenant-alpha"),
        name="Contract Review",
        current_node="supervisor",
    )
    snapshot = instance.transition_to(next_node="researcher", updated_state={"query": "laws"})
    assert instance.current_node == "researcher"
    assert instance.version == 2
    assert snapshot.version == 2
    assert snapshot.state_data["query"] == "laws"


def test_workflow_instance_transition_when_not_running_raises() -> None:
    instance = WorkflowInstance(
        workflow_id="wf-100",
        tenant_id=TenantId("tenant-alpha"),
        name="Contract Review",
        current_node="supervisor",
        status=WorkflowStatus.COMPLETED,
    )
    with pytest.raises(ValueError, match="No se puede realizar una transición"):
        instance.transition_to(next_node="researcher", updated_state={})
