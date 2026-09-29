"""Integration tests for workflow resumption from checkpoints."""

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.application.agents.services.state_reducer_service import StateReducerService
from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.entities.workflow_instance import WorkflowInstance
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.mssql.in_memory_workflow_checkpoint_repository import (
    InMemoryWorkflowCheckpointRepositoryAdapter,
)
from src.interfaces.http.api import build_api


class ApprovalStubExecutor(SubAgentExecutorPort):
    """Executor that halts execution on first step requiring operator approval."""

    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        if current_state.get("approved") is True:
            return {"final_output": "Database updated successfully"}
        return {
            "requires_approval": True,
            "approval_id": "appr-exec-1",
            "tool_name": "database_write",
        }


def create_approval_graph() -> WorkflowGraph:
    graph = WorkflowGraph(entry_node="action_node", end_nodes={"done_node"})
    graph.add_node("action_node", AgentRole.SPECIALIST)
    graph.add_node("done_node", AgentRole.CRITIC)
    graph.add_edge("action_node", "done_node")
    return graph


@pytest.fixture
def workflow_repo() -> InMemoryWorkflowCheckpointRepositoryAdapter:
    return InMemoryWorkflowCheckpointRepositoryAdapter()


@pytest.fixture
def approval_engine() -> GraphExecutionEngine:
    return GraphExecutionEngine(
        graph=create_approval_graph(),
        executor=ApprovalStubExecutor(),
        state_reducer=StateReducerService(),
    )


@pytest.mark.anyio
async def test_resume_workflow_endpoint(
    workflow_repo: InMemoryWorkflowCheckpointRepositoryAdapter,
    approval_engine: GraphExecutionEngine,
) -> None:
    app = build_api(
        workflow_checkpoint_repo=workflow_repo,
        graph_execution_engine=approval_engine,
    )
    tenant_id = "corp-acme"

    # Pre-seed a workflow in WAITING_APPROVAL
    instance = WorkflowInstance.create(
        workflow_id="wf-suspended-1",
        tenant_id=TenantId(tenant_id),
        name="Suspended Action",
        initial_node="action_node",
    )
    instance.mark_waiting_approval(approval_id="appr-exec-1", tool_name="database_write")
    workflow_repo.save_instance(instance)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Resume with operator approved status
        resume_payload = {
            "resumed_state_updates": {"approved": True},
        }
        resp = await client.post(
            f"/tenants/{tenant_id}/workflows/wf-suspended-1/resume",
            json=resume_payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_id"] == "wf-suspended-1"
        assert data["status"] in ("RUNNING", "COMPLETED")

        # Resuming a non-existent workflow returns 404
        not_found_resp = await client.post(
            f"/tenants/{tenant_id}/workflows/non-existent/resume",
            json=resume_payload,
        )
        assert not_found_resp.status_code == 404
