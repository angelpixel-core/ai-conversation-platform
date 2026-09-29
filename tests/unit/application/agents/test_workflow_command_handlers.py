"""Unit tests for StartWorkflow and ResumeWorkflow Command Handlers."""

import pytest

from src.application.agents.commands.resume_workflow_command import (
    ResumeWorkflowCommand,
    ResumeWorkflowCommandHandler,
)
from src.application.agents.commands.start_workflow_command import (
    StartWorkflowCommand,
    StartWorkflowCommandHandler,
)
from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.agents.services.graph_execution_engine import GraphExecutionEngine
from src.application.agents.services.state_reducer_service import StateReducerService
from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.agents.value_objects.state_snapshot import StateSnapshot
from src.domain.tenants.value_objects.tenant_id import TenantId


class InMemoryCheckpointRepo(WorkflowCheckpointRepositoryPort):
    def __init__(self) -> None:
        self.instances: dict[str, WorkflowInstance] = {}
        self.checkpoints: list[StateSnapshot] = []

    def save_checkpoint(self, snapshot: StateSnapshot) -> None:
        self.checkpoints.append(snapshot)

    def get_latest_checkpoint(self, tenant_id: TenantId, workflow_id: str) -> StateSnapshot | None:
        matching = [
            c for c in self.checkpoints if c.tenant_id == tenant_id and c.workflow_id == workflow_id
        ]
        return sorted(matching, key=lambda c: c.version, reverse=True)[0] if matching else None

    def list_checkpoints(self, tenant_id: TenantId, workflow_id: str) -> list[StateSnapshot]:
        return [
            c for c in self.checkpoints if c.tenant_id == tenant_id and c.workflow_id == workflow_id
        ]

    def save_instance(self, instance: WorkflowInstance) -> None:
        self.instances[f"{instance.tenant_id.value}:{instance.id}"] = instance

    def get_instance(self, tenant_id: TenantId, workflow_id: str) -> WorkflowInstance | None:
        return self.instances.get(f"{tenant_id.value}:{workflow_id}")


class DummyExecutor(SubAgentExecutorPort):
    async def execute_node(self, node_id: str, role: AgentRole, current_state: dict) -> dict:
        if node_id == "hitl_gate":
            if not current_state.get("is_approved"):
                return {"requires_approval": True, "approval_id": "appr-1", "tool_name": "db_drop"}
        return {f"{node_id}_done": True}


@pytest.mark.anyio
async def test_start_workflow_command_handler_success() -> None:
    repo = InMemoryCheckpointRepo()
    executor = DummyExecutor()
    reducer = StateReducerService()

    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_edge("supervisor", "end")

    engine = GraphExecutionEngine(graph=graph, executor=executor, state_reducer=reducer)
    handler = StartWorkflowCommandHandler(checkpoint_repo=repo, engine=engine)

    command = StartWorkflowCommand(
        tenant_id="corp-acme",
        workflow_id="wf-test-101",
        name="Contract Review",
        initial_state={"doc_id": "doc-55"},
    )

    result = await handler.handle(command)

    assert result.workflow_id == "wf-test-101"
    assert result.status == "COMPLETED"
    assert repo.get_instance(TenantId("corp-acme"), "wf-test-101") is not None
    assert repo.get_latest_checkpoint(TenantId("corp-acme"), "wf-test-101") is not None


@pytest.mark.anyio
async def test_resume_workflow_command_handler_success() -> None:
    repo = InMemoryCheckpointRepo()
    executor = DummyExecutor()
    reducer = StateReducerService()

    graph = WorkflowGraph(entry_node="hitl_gate", end_nodes={"end"})
    graph.add_node("hitl_gate", AgentRole.SPECIALIST)
    graph.add_edge("hitl_gate", "end")

    engine = GraphExecutionEngine(graph=graph, executor=executor, state_reducer=reducer)
    start_handler = StartWorkflowCommandHandler(checkpoint_repo=repo, engine=engine)
    resume_handler = ResumeWorkflowCommandHandler(checkpoint_repo=repo, engine=engine)

    # 1. Start workflow that pauses at hitl_gate
    await start_handler.handle(
        StartWorkflowCommand(
            tenant_id="corp-acme",
            workflow_id="wf-hitl-202",
            name="Destructive DB Action",
        )
    )

    instance = repo.get_instance(TenantId("corp-acme"), "wf-hitl-202")
    assert instance is not None
    assert instance.status == WorkflowStatus.WAITING_APPROVAL

    # 2. Operator approves and sends resumed state
    resume_cmd = ResumeWorkflowCommand(
        tenant_id="corp-acme",
        workflow_id="wf-hitl-202",
        resumed_state_updates={"is_approved": True, "operator_id": "admin@corp.com"},
    )

    resume_result = await resume_handler.handle(resume_cmd)

    assert resume_result.workflow_id == "wf-hitl-202"
    assert resume_result.status == "COMPLETED"
    assert instance.status == WorkflowStatus.COMPLETED
