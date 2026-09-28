"""Application dependency injection container (Composition Root) for the API service."""

import logging
from dataclasses import dataclass

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
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.routing.services.model_router_service import (
    ModelRouterService,
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
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommandHandler,
)
from src.application.tenants.commands.settle_quota_command import (
    SettleQuotaCommandHandler,
)
from src.application.tools.services.tool_policy_evaluator_service import (
    ToolPolicyEvaluatorService,
)
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepository,
)
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.knowledge.ports.knowledge_repository_port import (
    KnowledgeRepositoryPort,
)
from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.infrastructure.embeddings.fake_embedding_client import (
    FakeEmbeddingClientAdapter,
)
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryToolApprovalRepositoryAdapter,
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
    MssqlConversationRepository,
    MssqlIdempotencyRepository,
    MssqlKnowledgeRepository,
    MssqlStreamBufferRepository,
    MssqlToolApprovalRepository,
    MssqlUnitOfWork,
    create_mssql_engine,
    create_session_factory,
)
from src.infrastructure.routing.in_memory_model_catalog import (
    InMemoryModelCatalogAdapter,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
    get_settings,
)
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunner,
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
    model_catalog: ModelCatalogPort
    model_router_service: ModelRouterService
    reserve_quota_handler: ReserveQuotaCommandHandler
    settle_quota_handler: SettleQuotaCommandHandler
    retriever_service: HybridRetrieverService | None = None
    embedding_client: EmbeddingClientPort | None = None
    tool_approval_repo: ToolApprovalRepositoryPort | None = None
    tool_runner: SandboxedToolRunnerPort | None = None
    tool_policy_evaluator: ToolPolicyEvaluatorService | None = None


def create_app_container(
    settings: Settings | None = None,
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    model_catalog: ModelCatalogPort | None = None,
    embedding_client: EmbeddingClientPort | None = None,
    *,
    enable_tenant_middleware: bool | None = None,
) -> AppContainer:
    """Build and wire application dependencies into a cohesive container."""
    current_settings = settings or get_settings()
    read_repo: ConversationRepository | None = None
    read_knowledge_repo: KnowledgeRepositoryPort | None = None
    read_tool_approval_repo: ToolApprovalRepositoryPort | None = None

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
        try:
            read_knowledge_repo = uow.knowledge
        except RuntimeError:
            session_factory = getattr(uow, "_session_factory", None)
            if session_factory is not None:
                read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        try:
            read_tool_approval_repo = uow.tool_approvals
        except RuntimeError:
            session_factory = getattr(uow, "_session_factory", None)
            if session_factory is not None:
                read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
    elif current_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(current_settings.get_database_url())
        session_factory = create_session_factory(engine)
        uow = MssqlUnitOfWork(session_factory=session_factory)
        read_repo = MssqlConversationRepository(session=session_factory())
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
        read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
    else:
        uow = InMemoryUnitOfWork()
        read_repo = uow.conversations
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()
        read_knowledge_repo = uow.knowledge
        read_tool_approval_repo = uow.tool_approvals

    client = llm_client if llm_client is not None else FakeLlmClientAdapter()

    idempotent_executor = IdempotentCommandExecutor(idempotency_repo=idempotency_repo)
    stream_recovery_service = StreamRecoveryService(buffer_repo=stream_buffer_repo)

    create_handler = CreateConversationHandler(unit_of_work=uow)
    send_handler = SendMessageHandler(unit_of_work=uow)
    stream_handler = StreamConversationQueryHandler(
        conversation_repository=read_repo,
        llm_client=client,
    )

    catalog = model_catalog if model_catalog is not None else InMemoryModelCatalogAdapter()
    model_router = ModelRouterService(catalog=catalog)
    reserve_handler = ReserveQuotaCommandHandler(unit_of_work=uow)
    settle_handler = SettleQuotaCommandHandler(unit_of_work=uow)

    emb_client = embedding_client or FakeEmbeddingClientAdapter(dimension=1536)
    retriever_service = HybridRetrieverService(
        embedding_client=emb_client,
        knowledge_repository=read_knowledge_repo
        if read_knowledge_repo is not None
        else uow.knowledge,
    )
    tool_approval_repo = (
        read_tool_approval_repo
        if read_tool_approval_repo is not None
        else getattr(uow, "tool_approvals", None) or InMemoryToolApprovalRepositoryAdapter()
    )
    tool_runner = AnyioSandboxedToolRunner()
    tool_policy_evaluator = ToolPolicyEvaluatorService()

    use_tenant_middleware = (
        enable_tenant_middleware
        if enable_tenant_middleware is not None
        else current_settings.ENABLE_TENANT_MIDDLEWARE
    )

    fastapi_app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
        idempotent_executor=idempotent_executor,
        stream_recovery_service=stream_recovery_service,
        unit_of_work=uow,
        enable_tenant_middleware=use_tenant_middleware,
        retriever_service=retriever_service,
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
        model_catalog=catalog,
        model_router_service=model_router,
        reserve_quota_handler=reserve_handler,
        settle_quota_handler=settle_handler,
        retriever_service=retriever_service,
        embedding_client=emb_client,
        tool_approval_repo=tool_approval_repo,
        tool_runner=tool_runner,
        tool_policy_evaluator=tool_policy_evaluator,
    )


# Aliases for naming flexibility
Container = AppContainer
create_container = create_app_container
