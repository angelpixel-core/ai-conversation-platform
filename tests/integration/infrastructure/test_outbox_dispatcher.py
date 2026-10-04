"""Integration tests for Transactional Outbox Pattern and OutboxDispatcherAdapter (TDD)."""

from uuid import uuid4

import pytest

from src.application.shared.ports.event_publisher import EventPublisherPort
from src.infrastructure.shared.persistence.outbox.dispatcher import OutboxDispatcherAdapter
from src.infrastructure.shared.persistence.outbox.in_memory import (
    InMemoryOutboxRepositoryAdapter,
    OutboxMessage,
    OutboxStatus,
)


class DummyEventPublisher(EventPublisherPort):
    """Dummy event publisher supporting failure injection and event inspection."""

    def __init__(self, should_fail: bool = False) -> None:
        self.published_events: list[object] = []
        self.should_fail = should_fail

    def publish(self, event: object) -> None:
        if self.should_fail:
            raise RuntimeError("Broker connection timeout")
        self.published_events.append(event)


class AsyncDummyEventPublisher(EventPublisherPort):
    """Async event publisher to test coroutine publish method."""

    def __init__(self) -> None:
        self.published_events: list[object] = []

    async def publish(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        event: object,
    ) -> None:
        self.published_events.append(event)


def test_outbox_message_creation_sets_default_values() -> None:
    conv_id = uuid4()
    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=conv_id,
        event_type="MessageAppendedDomainEvent",
        payload='{"role": "user", "content": "Hello"}',
    )

    assert msg.id is not None
    assert msg.aggregate_type == "Conversation"
    assert msg.aggregate_id == conv_id
    assert msg.event_type == "MessageAppendedDomainEvent"
    assert msg.payload == '{"role": "user", "content": "Hello"}'
    assert msg.status == OutboxStatus.PENDING
    assert msg.created_at is not None
    assert msg.processed_at is None
    assert msg.retry_count == 0
    assert msg.error_message is None


def test_in_memory_outbox_repository_save_and_query() -> None:
    repo = InMemoryOutboxRepositoryAdapter()
    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="ConversationCreatedDomainEvent",
        payload="{}",
    )
    repo.save(msg)

    stored = repo.get_by_id(msg.id)
    assert stored is not None
    assert stored.id == msg.id

    pending = repo.get_pending()
    assert len(pending) == 1
    assert pending[0].id == msg.id

    msg.mark_completed()
    repo.save(msg)
    assert len(repo.get_pending()) == 0
    assert len(repo.all()) == 1


def test_in_memory_outbox_repository_add_compatibility() -> None:
    repo = InMemoryOutboxRepositoryAdapter()

    # Case 1: Add raw event string/object
    repo.add("RawEventPayload")
    assert len(repo.all()) == 1
    assert repo.all()[0].event_type == "str"

    # Case 2: Add OutboxMessage instance directly
    outbox_msg = OutboxMessage.create("Conversation", uuid4(), "CustomEvent", "{}")
    repo.add(outbox_msg)
    assert len(repo.all()) == 2
    assert repo.get_by_id(outbox_msg.id) == outbox_msg


@pytest.mark.anyio
async def test_outbox_dispatcher_processes_pending_messages() -> None:
    # Arrange
    repo = InMemoryOutboxRepositoryAdapter()
    publisher = DummyEventPublisher()
    dispatcher = OutboxDispatcherAdapter(repository=repo, event_publisher=publisher)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"content": "Hi"}',
    )
    repo.save(msg)

    # Act
    processed = await dispatcher.dispatch_pending()

    # Assert
    assert processed == 1
    assert msg.status == OutboxStatus.COMPLETED
    assert msg.processed_at is not None
    assert len(publisher.published_events) == 1
    assert publisher.published_events[0] == msg


@pytest.mark.anyio
async def test_outbox_dispatcher_marks_failed_on_publisher_error() -> None:
    # Arrange
    repo = InMemoryOutboxRepositoryAdapter()
    failing_publisher = DummyEventPublisher(should_fail=True)
    dispatcher = OutboxDispatcherAdapter(repository=repo, event_publisher=failing_publisher)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"content": "Error case"}',
    )
    repo.save(msg)

    # Act
    processed = await dispatcher.dispatch_pending()

    # Assert
    assert processed == 1
    assert msg.status == OutboxStatus.FAILED
    assert msg.retry_count == 1
    assert msg.error_message == "Broker connection timeout"
    assert len(repo.get_pending()) == 0


@pytest.mark.anyio
async def test_outbox_dispatcher_handles_async_publisher() -> None:
    # Arrange
    repo = InMemoryOutboxRepositoryAdapter()
    async_publisher = AsyncDummyEventPublisher()
    dispatcher = OutboxDispatcherAdapter(repository=repo, event_publisher=async_publisher)

    msg = OutboxMessage.create(
        aggregate_type="Conversation",
        aggregate_id=uuid4(),
        event_type="MessageAppendedDomainEvent",
        payload='{"content": "Async"}',
    )
    repo.save(msg)

    # Act
    processed = await dispatcher.dispatch_pending()

    # Assert
    assert processed == 1
    assert msg.status == OutboxStatus.COMPLETED
    assert len(async_publisher.published_events) == 1


@pytest.mark.anyio
async def test_outbox_dispatcher_returns_zero_when_no_pending_messages() -> None:
    repo = InMemoryOutboxRepositoryAdapter()
    publisher = DummyEventPublisher()
    dispatcher = OutboxDispatcherAdapter(repository=repo, event_publisher=publisher)

    processed = await dispatcher.dispatch_pending()

    assert processed == 0
    assert len(publisher.published_events) == 0
