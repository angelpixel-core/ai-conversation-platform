"""Unit tests for Agent Workflow Domain Events."""

from datetime import UTC, datetime

from src.domain.agents.events.workflow_events import (
    CheckpointSavedDomainEvent,
    SubAgentTaskDelegatedDomainEvent,
    WorkflowApprovalRequiredDomainEvent,
    WorkflowCompletedDomainEvent,
    WorkflowStartedDomainEvent,
)


def test_workflow_domain_events_instantiation() -> None:
    now = datetime.now(UTC)

    e1 = WorkflowStartedDomainEvent(
        workflow_id="wf-1",
        tenant_id="corp-acme",
        name="Contract Review",
        initial_node="supervisor",
        occurred_at=now,
    )
    assert e1.workflow_id == "wf-1"

    e2 = SubAgentTaskDelegatedDomainEvent(
        workflow_id="wf-1",
        tenant_id="corp-acme",
        from_node="supervisor",
        to_agent="researcher",
        subtask="Evaluate clauses",
        occurred_at=now,
    )
    assert e2.to_agent == "researcher"

    e3 = CheckpointSavedDomainEvent(
        workflow_id="wf-1",
        tenant_id="corp-acme",
        checkpoint_id="chk-1-2",
        node_id="researcher",
        version=2,
        occurred_at=now,
    )
    assert e3.version == 2

    e4 = WorkflowApprovalRequiredDomainEvent(
        workflow_id="wf-1",
        tenant_id="corp-acme",
        approval_id="appr-1",
        tool_name="sign_contract",
        occurred_at=now,
    )
    assert e4.tool_name == "sign_contract"

    e5 = WorkflowCompletedDomainEvent(
        workflow_id="wf-1",
        tenant_id="corp-acme",
        final_node="summarizer",
        occurred_at=now,
    )
    assert e5.final_node == "summarizer"
