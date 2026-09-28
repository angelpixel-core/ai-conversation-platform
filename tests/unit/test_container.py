"""Unit tests for Application Container composition root."""

from fastapi import FastAPI

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotentCommandExecutor,
)
from src.container import AppContainer, create_app_container
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
    MssqlIdempotencyRepository,
    MssqlStreamBufferRepository,
    MssqlUnitOfWork,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
)


def test_create_app_container_default_wires_in_memory() -> None:
    settings = Settings(PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY)
    container = create_app_container(settings=settings)

    assert isinstance(container, AppContainer)
    assert isinstance(container.unit_of_work, InMemoryUnitOfWork)
    assert isinstance(container.idempotency_repo, InMemoryIdempotencyRepositoryAdapter)
    assert isinstance(container.audit_repo, InMemoryAuditRepositoryAdapter)
    assert isinstance(container.stream_buffer_repo, InMemoryStreamBufferRepositoryAdapter)
    assert isinstance(container.stream_recovery_service, StreamRecoveryService)
    assert isinstance(container.idempotent_executor, IdempotentCommandExecutor)
    assert isinstance(container.create_conversation_handler, CreateConversationHandler)
    assert isinstance(container.send_message_handler, SendMessageHandler)
    assert isinstance(container.stream_conversation_handler, StreamConversationQueryHandler)
    assert isinstance(container.fastapi_app, FastAPI)


def test_create_app_container_with_mssql_driver() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.MSSQL,
        DATABASE_URL="sqlite:///:memory:",
    )
    container = create_app_container(settings=settings)

    assert isinstance(container, AppContainer)
    assert isinstance(container.unit_of_work, MssqlUnitOfWork)
    assert isinstance(container.idempotency_repo, MssqlIdempotencyRepository)
    assert isinstance(container.audit_repo, MssqlAuditRepository)
    assert isinstance(container.stream_buffer_repo, MssqlStreamBufferRepository)
    assert isinstance(container.stream_recovery_service, StreamRecoveryService)
    assert isinstance(container.idempotent_executor, IdempotentCommandExecutor)
    assert isinstance(container.fastapi_app, FastAPI)
