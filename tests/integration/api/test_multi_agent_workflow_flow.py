"""Integration tests for Multi-Agent Workflow HTTP endpoints and SSE streaming."""

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.application.agents.services.state_reducer_service import StateReducerService
from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.value_objects.agent_role import AgentRole
from src.infrastructure.persistence.mssql.in_memory_workflow_checkpoint_repository import (
    InMemoryWorkflowCheckpointRepositoryAdapter,
)
from src.interfaces.http.api import build_api


class StubSubAgentExecutor(SubAgentExecutorPort):
    """Stub subagent executor for deterministic integration testing."""

    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        if node_id == "supervisor":
            return {"plan": "delegate to researcher"}
        if node_id == "researcher":
            return {"findings": ["doc1", "doc2"], "final_output": "Research completed"}
        return {}


def create_test_graph() -> WorkflowGraph:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"researcher"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("researcher", AgentRole.SPECIALIST)
    graph.add_edge("supervisor", "researcher")
    return graph


@pytest.fixture
def workflow_repo() -> InMemoryWorkflowCheckpointRepositoryAdapter:
    return InMemoryWorkflowCheckpointRepositoryAdapter()


@pytest.fixture
def graph_engine() -> GraphExecutionEngine:
    return GraphExecutionEngine(
        graph=create_test_graph(),
        executor=StubSubAgentExecutor(),
        state_reducer=StateReducerService(),
    )


@pytest.mark.anyio
async def test_start_workflow_and_get_checkpoints(
    workflow_repo: InMemoryWorkflowCheckpointRepositoryAdapter,
    graph_engine: GraphExecutionEngine,
) -> None:
    app = build_api(
        workflow_checkpoint_repo=workflow_repo,
        graph_execution_engine=graph_engine,
    )
    tenant_id = "corp-acme"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Start workflow
        payload = {
            "name": "Market Research Flow",
            "initial_state": {"query": "vector databases"},
        }
        resp = await client.post(f"/tenants/{tenant_id}/workflows", json=payload)
        assert resp.status_code == 202
        data = resp.json()
        assert "workflow_id" in data
        workflow_id = data["workflow_id"]
        assert data["tenant_id"] == tenant_id
        assert data["name"] == "Market Research Flow"
        assert data["status"] == "COMPLETED"

        # 2. Get checkpoints
        cp_resp = await client.get(f"/tenants/{tenant_id}/workflows/{workflow_id}/checkpoints")
        assert cp_resp.status_code == 200
        checkpoints = cp_resp.json()
        assert len(checkpoints) >= 1
        assert checkpoints[0]["workflow_id"] == workflow_id
        assert checkpoints[0]["tenant_id"] == tenant_id

        # 3. Isolation: another tenant cannot see checkpoints
        other_resp = await client.get(f"/tenants/other-corp/workflows/{workflow_id}/checkpoints")
        assert other_resp.status_code == 200
        assert other_resp.json() == []


@pytest.mark.anyio
async def test_workflow_sse_streaming(
    workflow_repo: InMemoryWorkflowCheckpointRepositoryAdapter,
    graph_engine: GraphExecutionEngine,
) -> None:
    app = build_api(
        workflow_checkpoint_repo=workflow_repo,
        graph_execution_engine=graph_engine,
    )
    tenant_id = "corp-acme"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/tenants/{tenant_id}/workflows/wf-test/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "event: agent_handoff" in body or "event: subagent_completed" in body
