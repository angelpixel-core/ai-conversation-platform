"""Unit tests for WorkflowInstance Aggregate Root."""

import pytest

from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.events.workflow_events import (
    CheckpointSavedDomainEvent,
    SubAgentTaskDelegatedDomainEvent,
    WorkflowApprovalRequiredDomainEvent,
    WorkflowCompletedDomainEvent,
    WorkflowStartedDomainEvent,
)
from src.domain.agents.exceptions import InvalidGraphTransitionError
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_workflow_instance_initialization() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis Workflow",
        initial_node="supervisor",
        initial_state={"goal": "Analyze SLA obligations"},
    )

    assert instance.id == "wf-1001"
    assert instance.tenant_id == tenant
    assert instance.name == "Contract Analysis Workflow"
    assert instance.current_node == "supervisor"
    assert instance.status == WorkflowStatus.RUNNING
    assert instance.version == 1
    assert instance.state_data["goal"] == "Analyze SLA obligations"

    events = instance.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], WorkflowStartedDomainEvent)
    assert events[0].workflow_id == "wf-1001"
    assert events[0].tenant_id == "corp-acme"
    assert events[0].initial_node == "supervisor"


def test_workflow_instance_transition_success() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis",
        initial_node="supervisor",
    )
    instance.pull_events()

    snapshot = instance.transition_to(
        next_node="researcher",
        updated_state={"sources": ["doc_sla.pdf"]},
    )

    assert instance.current_node == "researcher"
    assert instance.version == 2
    assert snapshot.version == 2
    assert snapshot.workflow_id == "wf-1001"
    assert snapshot.current_node == "researcher"
    assert snapshot.state_data["sources"] == ["doc_sla.pdf"]

    events = instance.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], CheckpointSavedDomainEvent)
    assert events[0].workflow_id == "wf-1001"
    assert events[0].version == 2
    assert events[0].node_id == "researcher"


def test_workflow_instance_delegate_subagent_records_event() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis",
        initial_node="supervisor",
    )
    instance.pull_events()

    instance.delegate_subagent(
        from_node="supervisor",
        to_agent="researcher",
        subtask="Find penalty clauses",
    )

    events = instance.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], SubAgentTaskDelegatedDomainEvent)
    assert events[0].from_node == "supervisor"
    assert events[0].to_agent == "researcher"
    assert events[0].subtask == "Find penalty clauses"


def test_workflow_instance_mark_waiting_approval() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis",
        initial_node="action_node",
    )
    instance.pull_events()

    instance.mark_waiting_approval(approval_id="appr-555", tool_name="execute_refund")

    assert instance.status == WorkflowStatus.WAITING_APPROVAL
    events = instance.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], WorkflowApprovalRequiredDomainEvent)
    assert events[0].approval_id == "appr-555"
    assert events[0].tool_name == "execute_refund"


def test_workflow_instance_mark_completed() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis",
        initial_node="summarizer",
    )
    instance.pull_events()

    instance.mark_completed(final_output="Contract fully audited. No risks found.")

    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.state_data["final_output"] == "Contract fully audited. No risks found."
    events = instance.pull_events()
    assert len(events) == 1
    assert isinstance(events[0], WorkflowCompletedDomainEvent)
    assert events[0].workflow_id == "wf-1001"


def test_workflow_instance_transition_when_completed_raises_error() -> None:
    tenant = TenantId("corp-acme")
    instance = WorkflowInstance.create(
        workflow_id="wf-1001",
        tenant_id=tenant,
        name="Contract Analysis",
        initial_node="summarizer",
    )
    instance.mark_completed(final_output="Done")

    with pytest.raises(InvalidGraphTransitionError, match="COMPLETED"):
        instance.transition_to("another_node", {})
