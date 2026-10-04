"""Worker dependency injection container (Composition Root).

Assembles database connection, Unit of Work, LLM client, and RabbitMQ consumer
without any dependency on FastAPI or HTTP transport layers.
"""

import logging
from dataclasses import dataclass
from typing import Any

import anyio
import anyio.abc

from src.application.agents.ports.subagent_executor_port import (
    SubAgentExecutorPort,
)
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
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.governance.ports.incident_repository_port import (
    IncidentRepositoryPort,
)
from src.domain.governance.ports.pii_scanner_port import PiiScannerPort
from src.domain.governance.ports.safety_guardrail_port import (
    SafetyGuardrailPort,
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
from src.infrastructure.governance.anyio_stream_guardrail_filter import (
    AnyioStreamGuardrailFilter,
)
from src.infrastructure.governance.heuristic_injection_detector_adapter import (
    HeuristicInjectionDetectorAdapter,
)
from src.infrastructure.governance.regex_pii_scanner_adapter import (
    RegexPiiScannerAdapter,
)
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from src.infrastructure.messaging.rabbitmq.anyio_subagent_worker import (
    AnyioSubagentWorker,
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
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMQPublisherAdapter,
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
from src.infrastructure.persistence.in_memory.in_memory_incident_repository import (
    InMemoryIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.mssql import (
    InMemoryWorkflowCheckpointRepositoryAdapter,
    MssqlAuditRepository,
    MssqlIdempotencyRepository,
    MssqlKnowledgeRepository,
    MssqlStreamBufferRepository,
    MssqlToolApprovalRepository,
    MssqlUnitOfWork,
    MssqlWorkflowCheckpointRepository,
    create_mssql_engine,
    create_session_factory,
)
from src.infrastructure.persistence.mssql.mssql_incident_repository import (
    MssqlIncidentRepository,
)
from src.infrastructure.persistence.outbox.outbox_relay_service import (
    OutboxRelayService,
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
from src.infrastructure.telemetry.opentelemetry_config import setup_opentelemetry
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
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None = None
    subagent_worker: AnyioSubagentWorker | None = None
    incident_repo: IncidentRepositoryPort | None = None
    pii_scanner: PiiScannerPort | None = None
    safety_guardrail: SafetyGuardrailPort | None = None
    stream_guardrail_filter: AnyioStreamGuardrailFilter | None = None
    outbox_relay: OutboxRelayService | None = None

    async def start(self, task_group: anyio.abc.TaskGroup | None = None) -> None:
        """Initialize messaging topology (if applicable) and begin consuming."""
        if self.connection_manager is not None and self.topology_config is not None:
            logger.info("Declaring RabbitMQ topology for background worker...")
            channel = await self.connection_manager.get_channel()
            await self.topology_config.declare_topology(channel)

        if self.outbox_relay is not None and task_group is not None:
            logger.info("Starting outbox relay poller in background task...")
            task_group.start_soon(self.outbox_relay.run)

        logger.info("Starting background worker message consumption...")
        await self.consumer.start_consuming()

    async def stop(self) -> None:
        """Gracefully stop consuming and close broker connections."""
        if self.outbox_relay is not None:
            logger.info("Stopping outbox relay poller...")
            self.outbox_relay.stop()
        logger.info("Stopping background worker message consumption...")
        await self.consumer.stop_consuming()
        if self.connection_manager is not None:
            logger.info("Closing RabbitMQ connection...")
            await self.connection_manager.close()


def _wire_worker_persistence(
    settings: Settings,
    unit_of_work: UnitOfWork | None,
    incident_repo: IncidentRepositoryPort | None = None,
) -> tuple[
    UnitOfWork,
    Any,
    Any,
    Any,
    KnowledgeRepositoryPort | None,
    ToolApprovalRepositoryPort | None,
    IncidentRepositoryPort,
]:
    stream_buffer_repo = None
    audit_repo = None
    idempotency_repo = None
    read_knowledge_repo: KnowledgeRepositoryPort | None = None
    read_tool_approval_repo: ToolApprovalRepositoryPort | None = None

    if unit_of_work is not None:
        uow = unit_of_work
        session_factory = getattr(uow, "_session_factory", None)
        try:
            read_knowledge_repo = uow.knowledge
        except RuntimeError:
            if session_factory is not None:
                read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        try:
            read_tool_approval_repo = uow.tool_approvals
        except RuntimeError:
            if session_factory is not None:
                read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
        resolved_incident_repo = incident_repo or (
            getattr(uow, "incidents", None)
            or (
                MssqlIncidentRepository(session=session_factory)
                if session_factory is not None
                else InMemoryIncidentRepositoryAdapter()
            )
        )
    elif settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(settings.get_database_url())
        session_factory = create_session_factory(engine)
        uow = MssqlUnitOfWork(session_factory=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
        read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
        resolved_incident_repo = incident_repo or MssqlIncidentRepository(session=session_factory)
        from src.container import _seed_default_demo_tenant

        _seed_default_demo_tenant(uow)
    else:
        uow = InMemoryUnitOfWork()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
        read_knowledge_repo = uow.knowledge
        read_tool_approval_repo = uow.tool_approvals
        resolved_incident_repo = (
            incident_repo or getattr(uow, "incidents", None) or InMemoryIncidentRepositoryAdapter()
        )

    return (
        uow,
        stream_buffer_repo,
        audit_repo,
        idempotency_repo,
        read_knowledge_repo,
        read_tool_approval_repo,
        resolved_incident_repo,
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
                exchange_name=settings.BROKER_EXCHANGE,
                queue_name=settings.BROKER_QUEUE,
                dlx_exchange_name=settings.BROKER_DLX_EXCHANGE,
                dlq_name=settings.BROKER_DLQ,
                routing_key=settings.BROKER_ROUTING_KEY,
            )
        cons = RabbitMQConsumerAdapter(
            connection_manager=conn_mgr,
            queue_name=settings.BROKER_QUEUE,
            prefetch_count=settings.BROKER_PREFETCH_COUNT,
            queue_arguments={
                "x-dead-letter-exchange": settings.BROKER_DLX_EXCHANGE,
                "x-dead-letter-routing-key": settings.BROKER_ROUTING_KEY,
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
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None = None,
    subagent_executor: SubAgentExecutorPort | None = None,
    incident_repo: IncidentRepositoryPort | None = None,
    pii_scanner: PiiScannerPort | None = None,
    safety_guardrail: SafetyGuardrailPort | None = None,
    stream_guardrail_filter: AnyioStreamGuardrailFilter | None = None,
    outbox_relay: OutboxRelayService | None = None,
    *,
    enable_opentelemetry: bool | None = None,
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
        resolved_incident_repo,
    ) = _wire_worker_persistence(current_settings, unit_of_work, incident_repo)

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

    routing_key = topo.routing_key if topo is not None else current_settings.BROKER_ROUTING_KEY
    cons.subscribe(routing_key, worker_handler.handle)

    outbox_relay_service = outbox_relay
    if (
        outbox_relay_service is None
        and current_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL
        and current_settings.MESSAGING_DRIVER == MessagingDriver.RABBITMQ
    ):
        session_factory = getattr(uow, "_session_factory", None)
        if session_factory is not None and conn_mgr is not None:
            publisher = RabbitMQPublisherAdapter(
                connection_manager=conn_mgr,
                exchange_name=current_settings.BROKER_EXCHANGE,
            )
            outbox_relay_service = OutboxRelayService(
                session_factory=session_factory,
                message_broker=publisher,
                poll_interval=0.5,
            )

    tool_approval_repo = (
        read_tool_approval_repo
        if read_tool_approval_repo is not None
        else getattr(uow, "tool_approvals", None) or InMemoryToolApprovalRepositoryAdapter()
    )
    tool_runner = AnyioSandboxedToolRunner()
    tool_policy_evaluator = ToolPolicyEvaluatorService()

    if workflow_checkpoint_repo is not None:
        resolved_workflow_repo = workflow_checkpoint_repo
    elif current_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
        engine = create_mssql_engine(current_settings.get_database_url())
        session_factory = create_session_factory(engine)
        resolved_workflow_repo = MssqlWorkflowCheckpointRepository(session=session_factory)
    else:
        resolved_workflow_repo = InMemoryWorkflowCheckpointRepositoryAdapter()

    subagent_worker = (
        AnyioSubagentWorker(executor=subagent_executor) if subagent_executor is not None else None
    )

    use_otel = (
        enable_opentelemetry
        if enable_opentelemetry is not None
        else current_settings.ENABLE_OPENTELEMETRY
    )
    if use_otel:
        setup_opentelemetry(service_name=f"{current_settings.OTEL_SERVICE_NAME}-worker")

    pii_scanner_adapter = pii_scanner or RegexPiiScannerAdapter()
    safety_guardrail_adapter = safety_guardrail or HeuristicInjectionDetectorAdapter()
    stream_filter = (
        stream_guardrail_filter
        if stream_guardrail_filter is not None
        else AnyioStreamGuardrailFilter(guardrail=safety_guardrail_adapter)
    )

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
        workflow_checkpoint_repo=resolved_workflow_repo,
        subagent_worker=subagent_worker,
        incident_repo=resolved_incident_repo,
        pii_scanner=pii_scanner_adapter,
        safety_guardrail=safety_guardrail_adapter,
        stream_guardrail_filter=stream_filter,
        outbox_relay=outbox_relay_service,
    )
