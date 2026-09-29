"""Unit tests for GraphExecutionEngine using AnyIO."""

import anyio
import pytest

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.application.agents.services.state_reducer_service import StateReducerService
from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeSubAgentExecutor(SubAgentExecutorPort):
    def __init__(self) -> None:
        self.invocations: list[str] = []
        self.custom_returns: dict[str, dict] = {}
        self.raise_on: str | None = None

    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict,
    ) -> dict:
        self.invocations.append(node_id)
        if self.raise_on == node_id:
            raise RuntimeError(f"Error forzado en {node_id}")
        if node_id in self.custom_returns:
            return self.custom_returns[node_id]
        return {f"{node_id}_result": f"Output from {node_id}"}


@pytest.mark.anyio
async def test_graph_execution_engine_sequential_flow() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("researcher", AgentRole.SPECIALIST)
    graph.add_edge("supervisor", "researcher")
    graph.add_edge("researcher", "end")

    executor = FakeSubAgentExecutor()
    reducer = StateReducerService()
    engine = GraphExecutionEngine(graph=graph, executor=executor, state_reducer=reducer)

    instance = WorkflowInstance.create(
        workflow_id="wf-seq-1",
        tenant_id=TenantId("corp-acme"),
        name="Sequential Workflow",
        initial_node="supervisor",
        initial_state={"goal": "Audit"},
    )

    completed_instance = await engine.run_until_completion(instance)

    assert completed_instance.status == WorkflowStatus.COMPLETED
    assert completed_instance.current_node == "end"
    assert "supervisor_result" in completed_instance.state_data
    assert "researcher_result" in completed_instance.state_data
    assert executor.invocations == ["supervisor", "researcher"]


@pytest.mark.anyio
async def test_graph_execution_engine_parallel_branching() -> None:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"summarizer", "end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("researcher_a", AgentRole.SPECIALIST)
    graph.add_node("researcher_b", AgentRole.SPECIALIST)
    graph.add_node("summarizer", AgentRole.SUMMARIZER)

    graph.add_edge("supervisor", "researcher_a")
    graph.add_edge("supervisor", "researcher_b")
    graph.add_edge("researcher_a", "summarizer")
    graph.add_edge("researcher_b", "summarizer")
    graph.add_edge("summarizer", "end")

    executor = FakeSubAgentExecutor()
    executor.custom_returns["researcher_a"] = {"findings": ["clause_1"]}
    executor.custom_returns["researcher_b"] = {"findings": ["clause_2"]}

    reducer = StateReducerService()
    engine = GraphExecutionEngine(graph=graph, executor=executor, state_reducer=reducer)

    instance = WorkflowInstance.create(
        workflow_id="wf-parallel-1",
        tenant_id=TenantId("corp-acme"),
        name="Parallel Branches",
        initial_node="supervisor",
    )

    completed_instance = await engine.run_until_completion(instance)

    assert completed_instance.status == WorkflowStatus.COMPLETED
    assert "researcher_a" in executor.invocations
    assert "researcher_b" in executor.invocations
    assert "clause_1" in completed_instance.state_data["findings"]
    assert "clause_2" in completed_instance.state_data["findings"]


@pytest.mark.anyio
async def test_graph_execution_engine_hitl_suspension() -> None:
    graph = WorkflowGraph(entry_node="action_node", end_nodes={"end"})
    graph.add_node("action_node", AgentRole.SPECIALIST)
    graph.add_edge("action_node", "end")

    executor = FakeSubAgentExecutor()
    executor.custom_returns["action_node"] = {
        "requires_approval": True,
        "approval_id": "appr-999",
        "tool_name": "transfer_funds",
    }

    reducer = StateReducerService()
    engine = GraphExecutionEngine(graph=graph, executor=executor, state_reducer=reducer)

    instance = WorkflowInstance.create(
        workflow_id="wf-hitl-1",
        tenant_id=TenantId("corp-acme"),
        name="HITL Workflow",
        initial_node="action_node",
    )

    resumed_instance = await engine.run_until_completion(instance)

    assert resumed_instance.status == WorkflowStatus.WAITING_APPROVAL
    assert resumed_instance.current_node == "action_node"
