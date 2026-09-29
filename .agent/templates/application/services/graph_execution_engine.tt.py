"""GraphExecutionEngine service for executing multi-agent state graphs using AnyIO."""

from typing import Any

import anyio

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.agents.services.state_reducer_service import StateReducerService
from src.domain.agents.entities.workflow_graph import WorkflowGraph
from src.domain.agents.entities.workflow_instance import WorkflowInstance, WorkflowStatus
from src.domain.agents.value_objects.agent_role import AgentRole


class GraphExecutionEngine:
    """Executes state graphs with sequential transitions and parallel AnyIO task branching."""

    def __init__(
        self,
        graph: WorkflowGraph,
        executor: SubAgentExecutorPort,
        state_reducer: StateReducerService,
    ) -> None:
        self.graph = graph
        self.executor = executor
        self.state_reducer = state_reducer

    async def _execute_parallel_branches(
        self,
        candidate_nodes: list[str],
        state_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        async def _run_branch(node: str, accumulator: list[dict[str, Any]]) -> None:
            branch_role = self.graph.nodes.get(node, AgentRole.SPECIALIST)
            branch_out = await self.executor.execute_node(node, branch_role, state_data)
            accumulator.append(branch_out)

        async with anyio.create_task_group() as tg:
            for node in candidate_nodes:
                tg.start_soon(_run_branch, node, results)

        return results

    async def _handle_transition(
        self,
        instance: WorkflowInstance,
        next_nodes: list[str],
    ) -> bool:
        """Handles single or parallel transitions. Returns True if workflow should terminate."""
        if not next_nodes:
            instance.mark_completed(final_output=instance.state_data.get("final_output"))
            return True

        if len(next_nodes) == 1:
            next_node = next_nodes[0]
            if next_node in self.graph.end_nodes:
                instance.transition_to(next_node, {})
                instance.mark_completed(final_output=instance.state_data.get("final_output"))
                return True
            instance.transition_to(next_node, {})
            return False

        parallel_results = await self._execute_parallel_branches(next_nodes, instance.state_data)
        merged_state = self.state_reducer.reduce(instance.state_data, parallel_results)

        downstream_targets: set[str] = set()
        for node in next_nodes:
            downstream_targets.update(self.graph.get_next_nodes(node, merged_state))

        convergence_node = list(downstream_targets)[0] if downstream_targets else next_nodes[0]
        instance.transition_to(convergence_node, merged_state)
        return False

    async def run_until_completion(
        self,
        instance: WorkflowInstance,
        max_steps: int = 25,
    ) -> WorkflowInstance:
        """Executes the workflow graph until reaching an end node, approval gating, or max steps."""
        steps = 0
        while steps < max_steps and instance.status == WorkflowStatus.RUNNING:
            current_node = instance.current_node

            if current_node in self.graph.end_nodes:
                instance.mark_completed(final_output=instance.state_data.get("final_output"))
                break

            role = self.graph.nodes.get(current_node, AgentRole.SPECIALIST)
            output = await self.executor.execute_node(current_node, role, instance.state_data)

            if output.get("requires_approval") is True:
                approval_id = str(
                    output.get("approval_id") or f"appr-{instance.id}-{instance.version}"
                )
                tool_name = str(output.get("tool_name") or "unknown_tool")
                instance.mark_waiting_approval(approval_id=approval_id, tool_name=tool_name)
                break

            instance.state_data.update(output)
            next_nodes = self.graph.get_next_nodes(current_node, instance.state_data)

            should_terminate = await self._handle_transition(instance, next_nodes)
            if should_terminate:
                break

            steps += 1

        if steps >= max_steps and instance.status == WorkflowStatus.RUNNING:
            instance.mark_failed(reason="Exceeded maximum workflow steps.")

        return instance
