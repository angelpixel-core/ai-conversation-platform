"""Worker dependency injection container (Composition Root).

Assembles database connection, Unit of Work, LLM client, and RabbitMQ consumer
without any dependency on FastAPI or HTTP transport layers.
"""

import logging
from dataclasses import dataclass

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
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
from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
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
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
    MssqlIdempotencyRepository,
    MssqlStreamBufferRepository,
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


def create_worker_container(
    settings: Settings | None = None,
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    consumer: EventConsumerPort | None = None,
    connection_manager: RabbitMQConnectionManager | None = None,
    topology_config: RabbitMQTopologyConfig | None = None,
    fallback_llm_client: LlmClientPort | None = None,
    model_catalog: ModelCatalogPort | None = None,
) -> WorkerContainer:
    """Build and wire the autonomous background worker container."""
    current_settings = settings or get_settings()

    # 1. Wire Persistence
    stream_buffer_repo = None
    audit_repo = None
    idempotency_repo = None

    if unit_of_work is not None:
        uow = unit_of_work
    elif current_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(current_settings.get_database_url())
        session_factory = create_session_factory(engine)
        uow = MssqlUnitOfWork(session_factory=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
    else:
        uow = InMemoryUnitOfWork()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()

    # 2. Wire LLM Client
    client = llm_client if llm_client is not None else FakeLlmClientAdapter()

    catalog = model_catalog if model_catalog is not None else InMemoryModelCatalogAdapter()
    model_router = ModelRouterService(catalog=catalog)
    settle_handler = SettleQuotaCommandHandler(unit_of_work=uow)

    # 3. Wire Worker Handler
    worker_handler = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=client,
        stream_buffer_repo=stream_buffer_repo,
        audit_repo=audit_repo,
        idempotency_repo=idempotency_repo,
        fallback_llm_client=fallback_llm_client,
        settle_handler=settle_handler,
    )

    # 4. Wire Messaging / Consumer
    conn_mgr = connection_manager
    topo = topology_config

    if consumer is not None:
        cons = consumer
    elif current_settings.MESSAGING_DRIVER == MessagingDriver.RABBITMQ:
        if conn_mgr is None:
            conn_mgr = RabbitMQConnectionManager(url=current_settings.get_rabbitmq_url())
        if topo is None:
            topo = RabbitMQTopologyConfig(
                exchange_name=current_settings.RABBITMQ_EXCHANGE,
                queue_name=current_settings.RABBITMQ_QUEUE,
                dlx_exchange_name=current_settings.RABBITMQ_DLX_EXCHANGE,
                dlq_name=current_settings.RABBITMQ_DLQ,
                routing_key=current_settings.RABBITMQ_ROUTING_KEY,
            )
        cons = RabbitMQConsumerAdapter(
            connection_manager=conn_mgr,
            queue_name=current_settings.RABBITMQ_QUEUE,
            prefetch_count=current_settings.RABBITMQ_PREFETCH_COUNT,
            queue_arguments={
                "x-dead-letter-exchange": current_settings.RABBITMQ_DLX_EXCHANGE,
                "x-dead-letter-routing-key": current_settings.RABBITMQ_ROUTING_KEY,
            },
        )
    else:
        cons = InMemoryMessageBroker()

    # Subscribe worker handler to the routing key
    routing_key = topo.routing_key if topo is not None else current_settings.RABBITMQ_ROUTING_KEY
    cons.subscribe(routing_key, worker_handler.handle)

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
    )
