"""Integration tests for multi-tenant RabbitMQ routing topology and worker execution."""

from unittest.mock import AsyncMock

import pytest

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.domain.conversations.entities.conversation import Conversation
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


def test_format_tenant_routing_key() -> None:
    config = RabbitMQTopologyConfig()
    routing_key = config.format_tenant_routing_key(
        tenant_id="tenant-fintech-1",
        event_type="conversation.message.appended",
    )
    assert routing_key == "tenant.tenant-fintech-1.conversation.message.appended"


@pytest.mark.anyio
async def test_topology_declares_tenant_routing_bindings() -> None:
    config = RabbitMQTopologyConfig()
    channel_mock = AsyncMock()
    exchange_mock = AsyncMock()
    queue_mock = AsyncMock()
    dlx_mock = AsyncMock()
    dlq_mock = AsyncMock()

    channel_mock.declare_exchange.side_effect = [dlx_mock, exchange_mock]
    channel_mock.declare_queue.side_effect = [dlq_mock, queue_mock]

    result = await config.declare_topology(channel_mock)

    assert result.exchange == exchange_mock
    assert result.queue == queue_mock

    # Verify queue is bound to both standard and multi-tenant pattern
    bound_keys = [call.kwargs.get("routing_key") for call in queue_mock.bind.call_args_list]
    assert "conversation.message.appended" in bound_keys
    assert "tenant.*.conversation.message.appended" in bound_keys


@pytest.mark.anyio
async def test_worker_processes_routed_tenant_event_envelope() -> None:
    uow = InMemoryUnitOfWork()
    conv = Conversation.create(title="Routed Tenant Query")
    conv.append_user_message("Show dashboard stats")
    uow.conversations.add(conv)
    uow.commit()

    observed_tenants: list[str] = []

    class MockLlm(LlmClientPort):
        async def stream_chat(self, messages, temperature=0.7, max_tokens=1000):
            curr = get_current_tenant_id()
            if curr:
                observed_tenants.append(curr)
            yield "Dashboard rendered."

    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=MockLlm())

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(conv.id),
            "tenant_id": "tenant-saas-enterprise",
            "message": {"role": "user", "content": "Show dashboard stats"},
        },
    )

    await worker(envelope)

    assert observed_tenants == ["tenant-saas-enterprise"]
    saved_conv = uow.conversations.get(conv.id)
    assert saved_conv is not None
    assert saved_conv.messages[-1].content == "Dashboard rendered."
