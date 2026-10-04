"""Asynchronous subagent execution worker leveraging AnyIO for bounded concurrency."""

import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import anyio

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.shared.ports.event_publisher import EventPublisherPort
from src.domain.agents.events.workflow_events import SubAgentTaskDelegatedDomainEvent
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.shared.events.event_envelope import EventEnvelope

logger = logging.getLogger(__name__)


class AnyioSubagentWorker:
    """Consumes subagent tasks, delegates to SubAgentExecutorPort, and publishes domain events."""

    def __init__(
        self,
        executor: SubAgentExecutorPort,
        event_publisher: EventPublisherPort | None = None,
        concurrency_limit: int = 5,
    ) -> None:
        self._executor = executor
        self._event_publisher = event_publisher
        self._concurrency_limit = concurrency_limit

    def _parse_role(self, raw_role: Any) -> AgentRole:
        if isinstance(raw_role, AgentRole):
            return raw_role
        try:
            return AgentRole(str(raw_role).upper())
        except ValueError:
            return AgentRole.SPECIALIST

    async def process_subagent_task(
        self, envelope: EventEnvelope | dict[str, Any]
    ) -> dict[str, Any]:
        """Executes a single subagent task under bounded concurrency and error isolation."""
        payload: dict[str, Any] = (
            envelope.payload
            if isinstance(envelope, EventEnvelope)
            else envelope.get("payload", envelope)
        )

        tenant_id = str(payload.get("tenant_id", "")).strip()
        workflow_id = str(payload.get("workflow_id", "")).strip()
        node_id = str(payload.get("node_id", "")).strip()
        from_node = str(payload.get("from_node", "supervisor")).strip()
        current_state = payload.get("current_state", {})
        role = self._parse_role(payload.get("agent_role", AgentRole.SPECIALIST))

        start_time = time.perf_counter()
        try:
            output = await self._executor.execute_node(
                node_id=node_id,
                role=role,
                current_state=current_state,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if self._event_publisher is not None:
                self._event_publisher.publish(
                    SubAgentTaskDelegatedDomainEvent(
                        workflow_id=workflow_id,
                        tenant_id=tenant_id,
                        from_node=from_node,
                        to_agent=node_id,
                        subtask=str(current_state),
                        occurred_at=datetime.now(UTC),
                    )
                )

            return {
                "workflow_id": workflow_id,
                "node_id": node_id,
                "tenant_id": tenant_id,
                "output": output,
                "is_error": False,
                "execution_time_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                "Subagent execution failed for node %s in workflow %s",
                node_id,
                workflow_id,
            )
            return {
                "workflow_id": workflow_id,
                "node_id": node_id,
                "tenant_id": tenant_id,
                "output": {},
                "is_error": True,
                "error": str(exc),
                "execution_time_ms": elapsed_ms,
            }

    async def process_batch(
        self, envelopes: Sequence[EventEnvelope | dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Processes multiple subagent task envelopes concurrently with AnyIO TaskGroup."""
        results: list[dict[str, Any] | None] = [None] * len(envelopes)
        semaphore = anyio.Semaphore(self._concurrency_limit)

        async def _run_item(idx: int, env: EventEnvelope | dict[str, Any]) -> None:
            async with semaphore:
                res = await self.process_subagent_task(env)
                results[idx] = res

        async with anyio.create_task_group() as tg:
            for i, env in enumerate(envelopes):
                tg.start_soon(_run_item, i, env)

        return [r for r in results if r is not None]
