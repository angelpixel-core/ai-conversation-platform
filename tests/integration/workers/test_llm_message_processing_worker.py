"""Integration tests for LlmMessageProcessingWorker with real Microsoft SQL Server and RabbitMQ."""

import contextlib
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from uuid import uuid4

import anyio
import pytest

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.shared.events.event_envelope import EventEnvelope
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMQPublisherAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)
from src.infrastructure.persistence.mssql.unit_of_work import MssqlUnitOfWork
from src.worker_container import WorkerContainer


class RealStubLlmClient(LlmClientPort):
    """Stub LLM returning controlled tokens for integration tests."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        for token in self.tokens:
            yield token


class FatalErrorLlmClient(LlmClientPort):
    """Failing LLM to verify Dead Letter Queue dispatching."""

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        raise RuntimeError("External AI service permanently unavailable")
        yield ""  # pragma: no cover


@pytest.mark.anyio
async def test_worker_e2e_full_cycle_with_real_mssql_and_rabbitmq(
    clean_db: None,
    mssql_session_factory,
    rabbitmq_connection_manager: RabbitMQConnectionManager,
) -> None:
    suffix = uuid4().hex[:8]
    exchange_name = f"test.worker.events.{suffix}"
    queue_name = f"test.worker.queue.{suffix}"
    dlx_name = f"test.worker.dlx.{suffix}"
    dlq_name = f"test.worker.dlq.{suffix}"
    routing_key = f"test.worker.message.appended.{suffix}"

    topo = RabbitMQTopologyConfig(
        exchange_name=exchange_name,
        queue_name=queue_name,
        dlx_exchange_name=dlx_name,
        dlq_name=dlq_name,
        routing_key=routing_key,
    )
    channel = await rabbitmq_connection_manager.get_channel()
    declared = await topo.declare_topology(channel)

    try:
        # 1. Prepare conversation in MSSQL using test UoW
        test_uow = MssqlUnitOfWork(session_factory=mssql_session_factory)
        conversation = Conversation.create(title="E2E Architecture Session")
        conversation.append_user_message("Explain DDD tactical patterns.")
        with test_uow:
            test_uow.conversations.add(conversation)
            test_uow.commit()

        # 2. Wire Worker Container with dedicated worker UoW
        worker_uow = MssqlUnitOfWork(session_factory=mssql_session_factory)
        llm = RealStubLlmClient(["Entities", ", Value Objects", " and Aggregates."])
        consumer = RabbitMQConsumerAdapter(
            connection_manager=rabbitmq_connection_manager,
            queue_name=queue_name,
            passive=True,
        )
        worker_handler = LlmMessageProcessingWorker(unit_of_work=worker_uow, llm_client=llm)
        consumer.subscribe(routing_key, worker_handler.handle)

        container = WorkerContainer(
            unit_of_work=worker_uow,
            llm_client=llm,
            consumer=consumer,
            worker_handler=worker_handler,
            connection_manager=None,
            topology_config=None,
        )
        await container.start()

        # 3. Publish user message event to RabbitMQ
        publisher = RabbitMQPublisherAdapter(
            connection_manager=rabbitmq_connection_manager,
            exchange_name=exchange_name,
        )
        envelope = EventEnvelope.create(
            event_type="MessageAppendedDomainEvent",
            payload={
                "conversation_id": str(conversation.id),
                "message": {
                    "role": "user",
                    "content": "Explain DDD tactical patterns.",
                },
            },
        )
        await publisher.publish(topic=routing_key, envelope=envelope)

        # 4. Wait for worker to consume and persist assistant reply
        persisted = False
        for _ in range(50):
            await anyio.sleep(0.1)
            with test_uow:
                conv = test_uow.conversations.get(conversation.id)
                if conv is not None and len(conv.messages) == 2:
                    persisted = True
                    break

        await container.stop()

        assert persisted is True
        with test_uow:
            final_conv = test_uow.conversations.get(conversation.id)
            assert final_conv is not None
            assert len(final_conv.messages) == 2
            assistant_msg = final_conv.messages[1]
            assert assistant_msg.role == MessageRole.ASSISTANT
            assert assistant_msg.content == "Entities, Value Objects and Aggregates."

    finally:
        with contextlib.suppress(Exception):
            await declared.queue.delete()
        with contextlib.suppress(Exception):
            await declared.dlq.delete()
        with contextlib.suppress(Exception):
            await declared.exchange.delete()
        with contextlib.suppress(Exception):
            await declared.dlx_exchange.delete()


@pytest.mark.anyio
async def test_worker_routes_to_dlq_on_fatal_llm_failure(
    clean_db: None,
    mssql_session_factory,
    rabbitmq_connection_manager: RabbitMQConnectionManager,
) -> None:
    suffix = uuid4().hex[:8]
    exchange_name = f"test.worker.dlq.events.{suffix}"
    queue_name = f"test.worker.dlq.queue.{suffix}"
    dlx_name = f"test.worker.dlq.dlx.{suffix}"
    dlq_name = f"test.worker.dlq.dlq.{suffix}"
    routing_key = f"test.worker.dlq.message.appended.{suffix}"

    topo = RabbitMQTopologyConfig(
        exchange_name=exchange_name,
        queue_name=queue_name,
        dlx_exchange_name=dlx_name,
        dlq_name=dlq_name,
        routing_key=routing_key,
    )
    channel = await rabbitmq_connection_manager.get_channel()
    declared = await topo.declare_topology(channel)

    try:
        test_uow = MssqlUnitOfWork(session_factory=mssql_session_factory)
        conversation = Conversation.create(title="Failing LLM Session")
        conversation.append_user_message("Will fail.")
        with test_uow:
            test_uow.conversations.add(conversation)
            test_uow.commit()

        worker_uow = MssqlUnitOfWork(session_factory=mssql_session_factory)
        failing_llm = FatalErrorLlmClient()
        consumer = RabbitMQConsumerAdapter(
            connection_manager=rabbitmq_connection_manager,
            queue_name=queue_name,
            passive=True,
        )
        worker_handler = LlmMessageProcessingWorker(unit_of_work=worker_uow, llm_client=failing_llm)
        consumer.subscribe(routing_key, worker_handler.handle)

        container = WorkerContainer(
            unit_of_work=worker_uow,
            llm_client=failing_llm,
            consumer=consumer,
            worker_handler=worker_handler,
            connection_manager=None,
            topology_config=None,
        )
        await container.start()

        publisher = RabbitMQPublisherAdapter(
            connection_manager=rabbitmq_connection_manager,
            exchange_name=exchange_name,
        )
        envelope = EventEnvelope.create(
            event_type="MessageAppendedDomainEvent",
            payload={
                "conversation_id": str(conversation.id),
                "message": {
                    "role": "user",
                    "content": "Will fail.",
                },
            },
        )
        await publisher.publish(topic=routing_key, envelope=envelope)

        # Wait until DLQ receives the rejected message
        received_in_dlq = False
        received_body: dict | None = None

        dlq_chan = await rabbitmq_connection_manager.get_channel()
        dlq_obj = await dlq_chan.get_queue(dlq_name, ensure=False)

        for _ in range(50):
            await anyio.sleep(0.1)
            msg = await dlq_obj.get(no_ack=False, fail=False)
            if msg is not None:
                await msg.ack()
                received_body = json.loads(msg.body.decode("utf-8"))
                received_in_dlq = True
                break

        await container.stop()

        assert received_in_dlq is True
        assert received_body is not None
        assert received_body.get("payload", {}).get("conversation_id") == str(conversation.id)

    finally:
        with contextlib.suppress(Exception):
            await declared.queue.delete()
        with contextlib.suppress(Exception):
            await declared.dlq.delete()
        with contextlib.suppress(Exception):
            await declared.exchange.delete()
        with contextlib.suppress(Exception):
            await declared.dlx_exchange.delete()
