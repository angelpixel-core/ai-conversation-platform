"""Worker dependency injection container (Composition Root).

Assembles database connection, Unit of Work, LLM client, and RabbitMQ consumer
without any dependency on FastAPI or HTTP transport layers.
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.routing.services.model_router_service import (
    ModelRouterService,
)
from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.application.tenants.commands.settle_quota_command import (
    SettleQuotaCommandHandler,
)
from src.application.tools.services.tool_policy_evaluator_service import (
    ToolPolicyEvaluatorService,
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
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from src.infrastructure.messaging.rabbitmq.anyio_tool_execution_worker import (
    AnyioToolExecutionWorker,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_connection_manager import (
    RabbitMQConnectionManager,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_topology_config import (
    RabbitMQTopologyConfig,
)
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryToolApprovalRepositoryAdapter,
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
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
    MessagingDriver,
    PersistenceDriver,
    Settings,
    get_settings,
)
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunner,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkerContainer:
    """Encapsulates wired components and handles startup / shutdown lifecycle."""

    unit_of_work: UnitOfWork
    llm_client: LlmClientPort
    consumer: EventConsumerPort
    worker_handler: LlmMessageProcessingWorker
    settle_quota_handler: SettleQuotaCommandHandler | None = None
    model_router_service: ModelRouterService | None = None
    model_catalog: ModelCatalogPort | None = None
    connection_manager: RabbitMQConnectionManager | None = None
    topology_config: RabbitMQTopologyConfig | None = None
    retriever_service: HybridRetrieverService | None = None
    embedding_client: EmbeddingClientPort | None = None
    tool_approval_repo: ToolApprovalRepositoryPort | None = None
    tool_runner: SandboxedToolRunnerPort | None = None
    tool_policy_evaluator: ToolPolicyEvaluatorService | None = None
    tool_execution_worker: AnyioToolExecutionWorker | None = None

    async def start(self) -> None:
        """Initialize messaging topology (if applicable) and begin consuming."""
        if self.connection_manager is not None and self.topology_config is not None:
            logger.info("Declaring RabbitMQ topology for background worker...")
            channel = await self.connection_manager.get_channel()
            await self.topology_config.declare_topology(channel)

        logger.info("Starting background worker message consumption...")
        await self.consumer.start_consuming()

    async def stop(self) -> None:
        """Gracefully stop consuming and close broker connections."""
        logger.info("Stopping background worker message consumption...")
        await self.consumer.stop_consuming()
        if self.connection_manager is not None:
            logger.info("Closing RabbitMQ connection...")
            await self.connection_manager.close()


def _wire_worker_persistence(
    settings: Settings,
    unit_of_work: UnitOfWork | None,
) -> tuple[
    UnitOfWork,
    Any,
    Any,
    Any,
    KnowledgeRepositoryPort | None,
    ToolApprovalRepositoryPort | None,
]:
    stream_buffer_repo = None
    audit_repo = None
    idempotency_repo = None
    read_knowledge_repo: KnowledgeRepositoryPort | None = None
    read_tool_approval_repo: ToolApprovalRepositoryPort | None = None

    if unit_of_work is not None:
        uow = unit_of_work
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
    elif settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(settings.get_database_url())
        session_factory = create_session_factory(engine)
        uow = MssqlUnitOfWork(session_factory=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
        read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
    else:
        uow = InMemoryUnitOfWork()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
        read_knowledge_repo = uow.knowledge
        read_tool_approval_repo = uow.tool_approvals

    return (
        uow,
        stream_buffer_repo,
        audit_repo,
        idempotency_repo,
        read_knowledge_repo,
        read_tool_approval_repo,
    )


def _wire_worker_consumer(
    settings: Settings,
    consumer: EventConsumerPort | None,
    connection_manager: RabbitMQConnectionManager | None,
    topology_config: RabbitMQTopologyConfig | None,
) -> tuple[EventConsumerPort, RabbitMQConnectionManager | None, RabbitMQTopologyConfig | None]:
    conn_mgr = connection_manager
    topo = topology_config

    if consumer is not None:
        return consumer, conn_mgr, topo

    if settings.MESSAGING_DRIVER == MessagingDriver.RABBITMQ:
        if conn_mgr is None:
            conn_mgr = RabbitMQConnectionManager(url=settings.get_rabbitmq_url())
        if topo is None:
            topo = RabbitMQTopologyConfig(
                exchange_name=settings.RABBITMQ_EXCHANGE,
                queue_name=settings.RABBITMQ_QUEUE,
                dlx_exchange_name=settings.RABBITMQ_DLX_EXCHANGE,
                dlq_name=settings.RABBITMQ_DLQ,
                routing_key=settings.RABBITMQ_ROUTING_KEY,
            )
        cons = RabbitMQConsumerAdapter(
            connection_manager=conn_mgr,
            queue_name=settings.RABBITMQ_QUEUE,
            prefetch_count=settings.RABBITMQ_PREFETCH_COUNT,
            queue_arguments={
                "x-dead-letter-exchange": settings.RABBITMQ_DLX_EXCHANGE,
                "x-dead-letter-routing-key": settings.RABBITMQ_ROUTING_KEY,
            },
        )
        return cons, conn_mgr, topo

    return InMemoryMessageBroker(), conn_mgr, topo


def create_worker_container(
    settings: Settings | None = None,
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    consumer: EventConsumerPort | None = None,
    connection_manager: RabbitMQConnectionManager | None = None,
    topology_config: RabbitMQTopologyConfig | None = None,
    fallback_llm_client: LlmClientPort | None = None,
    model_catalog: ModelCatalogPort | None = None,
    embedding_client: EmbeddingClientPort | None = None,
) -> WorkerContainer:
    """Build and wire the autonomous background worker container."""
    current_settings = settings or get_settings()

    (
        uow,
        stream_buffer_repo,
        audit_repo,
        idempotency_repo,
        read_knowledge_repo,
        read_tool_approval_repo,
    ) = _wire_worker_persistence(current_settings, unit_of_work)

    client = llm_client if llm_client is not None else FakeLlmClientAdapter()
    catalog = model_catalog if model_catalog is not None else InMemoryModelCatalogAdapter()
    model_router = ModelRouterService(catalog=catalog)
    settle_handler = SettleQuotaCommandHandler(unit_of_work=uow)

    emb_client = embedding_client or FakeEmbeddingClientAdapter(dimension=1536)
    retriever_service = HybridRetrieverService(
        embedding_client=emb_client,
        knowledge_repository=read_knowledge_repo
        if read_knowledge_repo is not None
        else uow.knowledge,
    )

    worker_handler = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=client,
        stream_buffer_repo=stream_buffer_repo,
        audit_repo=audit_repo,
        idempotency_repo=idempotency_repo,
        fallback_llm_client=fallback_llm_client,
        settle_handler=settle_handler,
        retriever=retriever_service,
    )

    cons, conn_mgr, topo = _wire_worker_consumer(
        current_settings, consumer, connection_manager, topology_config
    )

    routing_key = topo.routing_key if topo is not None else current_settings.RABBITMQ_ROUTING_KEY
    cons.subscribe(routing_key, worker_handler.handle)

    tool_approval_repo = (
        read_tool_approval_repo
        if read_tool_approval_repo is not None
        else getattr(uow, "tool_approvals", None) or InMemoryToolApprovalRepositoryAdapter()
    )
    tool_runner = AnyioSandboxedToolRunner()
    tool_policy_evaluator = ToolPolicyEvaluatorService()

    return WorkerContainer(
        unit_of_work=uow,
        llm_client=client,
        consumer=cons,
        worker_handler=worker_handler,
        settle_quota_handler=settle_handler,
        model_router_service=model_router,
        model_catalog=catalog,
        connection_manager=conn_mgr,
        topology_config=topo,
        retriever_service=retriever_service,
        embedding_client=emb_client,
        tool_approval_repo=tool_approval_repo,
        tool_runner=tool_runner,
        tool_policy_evaluator=tool_policy_evaluator,
    )
