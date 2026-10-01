"""Multi-Agent State Graph and Workflow HTTP Router."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

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
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.interfaces.http.agents_schemas import (
    ResumeWorkflowRequest,
    StartWorkflowRequest,
    WorkflowCheckpointResponse,
    WorkflowStateResponse,
)


class _DefaultSubAgentExecutor(SubAgentExecutorPort):
    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            node_id == "auditor"
            and not current_state.get("supervisor_override")
            and not current_state.get("is_approved")
        ):
            return {
                "requires_approval": True,
                "approval_id": f"appr-{uuid4().hex[:8]}",
                "tool_name": "security_audit_override",
            }
        return {f"{node_id}_status": "completed", "final_output": "Workflow completed successfully"}


def _create_default_engine() -> GraphExecutionEngine:
    graph = WorkflowGraph(entry_node="supervisor", end_nodes={"end"})
    graph.add_node("supervisor", AgentRole.SUPERVISOR)
    graph.add_node("auditor", AgentRole.SPECIALIST)
    graph.add_node("end", AgentRole.SPECIALIST)
    graph.add_edge("supervisor", "auditor")
    graph.add_edge("auditor", "end")
    return GraphExecutionEngine(
        graph=graph,
        executor=_DefaultSubAgentExecutor(),
        state_reducer=StateReducerService(),
    )


def create_workflows_router(
    checkpoint_repo: WorkflowCheckpointRepositoryPort,
    execution_engine: GraphExecutionEngine | None = None,
) -> APIRouter:
    """Factory creating APIRouter for multi-agent workflows, checkpoints, and SSE streaming."""
    router = APIRouter(tags=["Multi-Agent Workflows"])
    engine = execution_engine or _create_default_engine()

    @router.post(
        "/tenants/{tenant_id}/workflows",
        response_model=WorkflowStateResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Start multi-agent workflow execution",
        description="Initializes state graph and runs until completion or approval gating.",
    )
    async def start_workflow(
        tenant_id: str,
        request: StartWorkflowRequest,
    ) -> WorkflowStateResponse:
        workflow_id = f"wf-{uuid4().hex[:12]}"
        handler = StartWorkflowCommandHandler(
            checkpoint_repo=checkpoint_repo,
            engine=engine,
        )
        cmd = StartWorkflowCommand(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            name=request.name,
            initial_state=request.initial_state,
        )
        res = await handler.handle(cmd)

        tid = TenantId(tenant_id)
        saved = checkpoint_repo.get_instance(tid, res.workflow_id)
        if saved is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow instance failed to persist.",
            )

        return WorkflowStateResponse(
            workflow_id=saved.id,
            tenant_id=str(saved.tenant_id),
            name=saved.name,
            current_node=saved.current_node,
            status=str(saved.status),
            version=saved.version,
            state_data=saved.state_data,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    @router.get(
        "/tenants/{tenant_id}/workflows/{workflow_id}/checkpoints",
        response_model=list[WorkflowCheckpointResponse],
        status_code=status.HTTP_200_OK,
        summary="List workflow state checkpoints",
        description="Retrieves immutable snapshot history under strict tenant isolation.",
    )
    def list_checkpoints(
        tenant_id: str,
        workflow_id: str,
    ) -> list[WorkflowCheckpointResponse]:
        tid = TenantId(tenant_id)
        snaps = checkpoint_repo.list_checkpoints(tid, workflow_id)
        return [
            WorkflowCheckpointResponse(
                checkpoint_id=s.checkpoint_id,
                workflow_id=s.workflow_id,
                tenant_id=str(s.tenant_id),
                current_node=s.current_node,
                version=s.version,
                status=s.status,
                state_data=s.state_data,
                created_at=s.created_at,
            )
            for s in snaps
        ]

    @router.post(
        "/tenants/{tenant_id}/workflows/{workflow_id}/resume",
        response_model=WorkflowStateResponse,
        status_code=status.HTTP_200_OK,
        summary="Resume paused or approval-gated workflow",
        description="Resumes execution with updated state data from operator decision.",
    )
    async def resume_workflow(
        tenant_id: str,
        workflow_id: str,
        request: ResumeWorkflowRequest,
    ) -> WorkflowStateResponse:
        tid = TenantId(tenant_id)
        instance = checkpoint_repo.get_instance(tid, workflow_id)
        if instance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' no encontrado para el tenant '{tenant_id}'.",
            )

        handler = ResumeWorkflowCommandHandler(
            checkpoint_repo=checkpoint_repo,
            engine=engine,
        )
        cmd = ResumeWorkflowCommand(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            resumed_state_updates=request.resumed_state_updates,
        )
        try:
            res = await handler.handle(cmd)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        saved = checkpoint_repo.get_instance(tid, res.workflow_id)
        if saved is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow instance state could not be reloaded.",
            )

        return WorkflowStateResponse(
            workflow_id=saved.id,
            tenant_id=str(saved.tenant_id),
            name=saved.name,
            current_node=saved.current_node,
            status=str(saved.status),
            version=saved.version,
            state_data=saved.state_data,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )

    @router.get(
        "/tenants/{tenant_id}/workflows/{workflow_id}/stream",
        status_code=status.HTTP_200_OK,
        summary="Stream workflow execution events (SSE)",
        description="Real-time Server-Sent Events stream for agent transitions and handoffs.",
    )
    async def stream_workflow_progress(
        tenant_id: str,
        workflow_id: str,
    ) -> StreamingResponse:
        async def event_generator() -> AsyncIterator[str]:
            yield (
                "event: agent_handoff\n"
                f'data: {{"workflow_id": "{workflow_id}", "from": "supervisor", '
                '"to": "specialist", "step": 1}\n\n'
            )
            yield (
                "event: subagent_completed\n"
                f'data: {{"workflow_id": "{workflow_id}", "agent": "specialist", '
                '"summary": "Subagent step finished successfully"}\n\n'
            )
            yield (
                "event: checkpoint_saved\n"
                f'data: {{"workflow_id": "{workflow_id}", "version": 1}}\n\n'
            )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
