"""Unit tests for MultiAgentTopologyConfig and AnyioSubagentWorker."""

from typing import Any

import pytest

from src.application.agents.ports.subagent_executor_port import SubAgentExecutorPort
from src.application.shared.ports.event_publisher import EventPublisherPort
from src.domain.agents.value_objects.agent_role import AgentRole
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.anyio_subagent_worker import AnyioSubagentWorker
from src.infrastructure.messaging.rabbitmq.multi_agent_topology_config import (
    MultiAgentTopologyConfig,
)


class FakeSubAgentExecutor(SubAgentExecutorPort):
    """Test fake for SubAgentExecutorPort."""

    def __init__(self, delay: float = 0.0, should_fail: bool = False) -> None:
        self.delay = delay
        self.should_fail = should_fail
        self.calls: list[tuple[str, AgentRole, dict[str, Any]]] = []

    async def execute_node(
        self,
        node_id: str,
        role: AgentRole,
        current_state: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append((node_id, role, current_state))
        if self.delay > 0:
            import anyio

            await anyio.sleep(self.delay)
        if self.should_fail:
            raise RuntimeError(f"Execution failed for node {node_id}")
        return {"output": f"completed_{node_id}", "status": "success"}


class FakeEventPublisher(EventPublisherPort):
    """Test fake for EventPublisher."""

    def __init__(self) -> None:
        self.published_events: list[Any] = []

    def publish(self, event: Any) -> None:
        self.published_events.append(event)


def test_multi_agent_topology_config() -> None:
    config = MultiAgentTopologyConfig()
    assert config.exchange_name == "ai_platform.agents"
    assert config.dlx_exchange_name == "ai_platform.agents.dlx"
    assert config.dlq_name == "agent.dead_letter.queue"
    assert "agent.supervisor.queue" in config.queues
    assert "agent.specialist.queue" in config.queues
    assert "agent.reviewer.queue" in config.queues

    routing_key = config.format_tenant_routing_key(tenant_id="corp-acme", event_type="specialist")
    assert routing_key == "tenant.corp-acme.agent.specialist"


@pytest.mark.anyio
async def test_subagent_worker_executes_single_task() -> None:
    executor = FakeSubAgentExecutor()
    publisher = FakeEventPublisher()
    worker = AnyioSubagentWorker(
        executor=executor,
        event_publisher=publisher,
        concurrency_limit=3,
    )

    payload = {
        "tenant_id": "corp-acme",
        "workflow_id": "wf-100",
        "node_id": "researcher_node",
        "agent_role": "SPECIALIST",
        "current_state": {"query": "deep learning architectures"},
    }
    envelope = EventEnvelope.create(event_type="SubAgentTaskDelegated", payload=payload)

    result = await worker.process_subagent_task(envelope)

    assert result["is_error"] is False
    assert result["workflow_id"] == "wf-100"
    assert result["node_id"] == "researcher_node"
    assert result["output"]["output"] == "completed_researcher_node"
    assert result["execution_time_ms"] >= 0.0

    assert len(executor.calls) == 1
    assert executor.calls[0][0] == "researcher_node"
    assert executor.calls[0][1] == AgentRole.SPECIALIST
    assert len(publisher.published_events) == 1


@pytest.mark.anyio
async def test_subagent_worker_handles_execution_error() -> None:
    executor = FakeSubAgentExecutor(should_fail=True)
    publisher = FakeEventPublisher()
    worker = AnyioSubagentWorker(executor=executor, event_publisher=publisher)

    payload = {
        "tenant_id": "corp-acme",
        "workflow_id": "wf-200",
        "node_id": "broken_node",
        "agent_role": "REVIEWER",
        "current_state": {},
    }

    result = await worker.process_subagent_task(payload)

    assert result["is_error"] is True
    assert "Execution failed for node broken_node" in result["error"]
    assert result["output"] == {}


@pytest.mark.anyio
async def test_subagent_worker_batch_execution_with_concurrency() -> None:
    executor = FakeSubAgentExecutor(delay=0.01)
    worker = AnyioSubagentWorker(executor=executor, concurrency_limit=2)

    envelopes = [
        {
            "tenant_id": "corp-acme",
            "workflow_id": f"wf-{i}",
            "node_id": f"node_{i}",
            "agent_role": "SPECIALIST",
            "current_state": {"idx": i},
        }
        for i in range(4)
    ]

    results = await worker.process_batch(envelopes)

    assert len(results) == 4
    for i, res in enumerate(results):
        assert res["workflow_id"] == f"wf-{i}"
        assert res["node_id"] == f"node_{i}"
        assert res["is_error"] is False
