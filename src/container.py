"""Application dependency injection container (Composition Root) for the API service."""

from dataclasses import dataclass
import logging

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
from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepository,
)
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
    MssqlConversationRepository,
    MssqlIdempotencyRepository,
    MssqlStreamBufferRepository,
    MssqlUnitOfWork,
    create_mssql_engine,
    create_session_factory,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
    get_settings,
)
from src.interfaces.http.api import build_api

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    """Encapsulates wired components and dependencies for the HTTP application."""

    unit_of_work: UnitOfWork
    llm_client: LlmClientPort
    idempotency_repo: IdempotencyRepositoryPort
    idempotent_executor: IdempotentCommandExecutor
    audit_repo: AuditRepositoryPort
    stream_buffer_repo: StreamBufferRepositoryPort
    stream_recovery_service: StreamRecoveryService
    create_conversation_handler: CreateConversationHandler
    send_message_handler: SendMessageHandler
    stream_conversation_handler: StreamConversationQueryHandler
    fastapi_app: FastAPI


def create_app_container(
    settings: Settings | None = None,
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
) -> AppContainer:
    """Build and wire application dependencies into a cohesive container."""
    current_settings = settings or get_settings()
    read_repo: ConversationRepository | None = None

    if unit_of_work is not None:
        uow = unit_of_work
        idempotency_repo: IdempotencyRepositoryPort = (
            getattr(uow, "idempotency", None) or InMemoryIdempotencyRepositoryAdapter()
        )
        audit_repo: AuditRepositoryPort = (
            getattr(uow, "audit", None) or InMemoryAuditRepositoryAdapter()
        )
        stream_buffer_repo: StreamBufferRepositoryPort = (
            getattr(uow, "stream_buffer", None) or InMemoryStreamBufferRepositoryAdapter()
        )
        try:
            read_repo = uow.conversations
        except RuntimeError:
            session_factory = getattr(uow, "_session_factory", None)
            if session_factory is not None:
                read_repo = MssqlConversationRepository(session=session_factory())
    elif current_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(current_settings.get_database_url())
        session_factory = create_session_factory(engine)
        uow = MssqlUnitOfWork(session_factory=session_factory)
        read_repo = MssqlConversationRepository(session=session_factory())
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
    else:
        uow = InMemoryUnitOfWork()
        read_repo = uow.conversations
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()

    client = llm_client if llm_client is not None else FakeLlmClientAdapter()

    idempotent_executor = IdempotentCommandExecutor(idempotency_repo=idempotency_repo)
    stream_recovery_service = StreamRecoveryService(buffer_repo=stream_buffer_repo)

    create_handler = CreateConversationHandler(unit_of_work=uow)
    send_handler = SendMessageHandler(unit_of_work=uow)
    stream_handler = StreamConversationQueryHandler(
        conversation_repository=read_repo,
        llm_client=client,
    )

    fastapi_app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
        idempotent_executor=idempotent_executor,
        stream_recovery_service=stream_recovery_service,
    )

    return AppContainer(
        unit_of_work=uow,
        llm_client=client,
        idempotency_repo=idempotency_repo,
        idempotent_executor=idempotent_executor,
        audit_repo=audit_repo,
        stream_buffer_repo=stream_buffer_repo,
        stream_recovery_service=stream_recovery_service,
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
        fastapi_app=fastapi_app,
    )


# Aliases for naming flexibility
Container = AppContainer
create_container = create_app_container
