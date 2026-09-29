"""Application dependency injection container (Composition Root) for the API service."""

import logging
from dataclasses import dataclass

from fastapi import FastAPI

from src.application.agents.services.graph_execution_engine import (
    GraphExecutionEngine,
)
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
from src.application.governance.services.guardrail_pipeline_service import (
    SafetyGuardrailPipelineService,
)
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.routing.services.model_router_service import (
    ModelRouterService,
)
from src.application.shared.governance.guarded_command_executor import (
    GuardedCommandExecutor,
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
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepository,
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
from src.infrastructure.governance.heuristic_injection_detector_adapter import (
    HeuristicInjectionDetectorAdapter,
)
from src.infrastructure.governance.regex_pii_scanner_adapter import (
    RegexPiiScannerAdapter,
)
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
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
    MssqlConversationRepository,
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
from src.infrastructure.routing.in_memory_model_catalog import (
    InMemoryModelCatalogAdapter,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
    get_settings,
)
from src.infrastructure.telemetry.opentelemetry_config import setup_opentelemetry
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
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None = None
    graph_execution_engine: GraphExecutionEngine | None = None
    incident_repo: IncidentRepositoryPort | None = None
    pii_scanner: PiiScannerPort | None = None
    safety_guardrail: SafetyGuardrailPort | None = None
    guardrail_pipeline: SafetyGuardrailPipelineService | None = None
    guarded_executor: GuardedCommandExecutor | None = None


def _wire_app_persistence(
    settings: Settings,
    unit_of_work: UnitOfWork | None,
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None,
    incident_repo: IncidentRepositoryPort | None = None,
) -> tuple[
    UnitOfWork,
    ConversationRepository,
    IdempotencyRepositoryPort,
    AuditRepositoryPort,
    StreamBufferRepositoryPort,
    KnowledgeRepositoryPort | None,
    ToolApprovalRepositoryPort | None,
    WorkflowCheckpointRepositoryPort,
    IncidentRepositoryPort,
]:
    read_repo: ConversationRepository | None = None
    read_knowledge_repo: KnowledgeRepositoryPort | None = None
    read_tool_approval_repo: ToolApprovalRepositoryPort | None = None

    if unit_of_work is not None:
        uow = unit_of_work
        idempotency_repo = (
            getattr(uow, "idempotency", None) or InMemoryIdempotencyRepositoryAdapter()
        )
        audit_repo = getattr(uow, "audit", None) or InMemoryAuditRepositoryAdapter()
        stream_buffer_repo = (
            getattr(uow, "stream_buffer", None) or InMemoryStreamBufferRepositoryAdapter()
        )
        session_factory = getattr(uow, "_session_factory", None)
        try:
            read_repo = uow.conversations
        except RuntimeError:
            if session_factory is not None:
                read_repo = MssqlConversationRepository(session=session_factory())
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
        resolved_workflow_repo = workflow_checkpoint_repo or (
            MssqlWorkflowCheckpointRepository(session=session_factory())
            if session_factory is not None
            else InMemoryWorkflowCheckpointRepositoryAdapter()
        )
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
        read_repo = MssqlConversationRepository(session=session_factory())
        idempotency_repo = MssqlIdempotencyRepository(session=session_factory)
        audit_repo = MssqlAuditRepository(session=session_factory)
        stream_buffer_repo = MssqlStreamBufferRepository(session=session_factory)
        read_knowledge_repo = MssqlKnowledgeRepository(session=session_factory())
        read_tool_approval_repo = MssqlToolApprovalRepository(session=session_factory())
        resolved_workflow_repo = workflow_checkpoint_repo or MssqlWorkflowCheckpointRepository(
            session=session_factory()
        )
        resolved_incident_repo = incident_repo or MssqlIncidentRepository(session=session_factory)

    else:
        uow = InMemoryUnitOfWork()
        read_repo = uow.conversations
        idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
        audit_repo = InMemoryAuditRepositoryAdapter()
        stream_buffer_repo = InMemoryStreamBufferRepositoryAdapter()
        read_knowledge_repo = uow.knowledge
        read_tool_approval_repo = uow.tool_approvals
        resolved_workflow_repo = (
            workflow_checkpoint_repo or InMemoryWorkflowCheckpointRepositoryAdapter()
        )
        resolved_incident_repo = (
            incident_repo or getattr(uow, "incidents", None) or InMemoryIncidentRepositoryAdapter()
        )

    if read_repo is None:
        read_repo = uow.conversations

    return (
        uow,
        read_repo,
        idempotency_repo,
        audit_repo,
        stream_buffer_repo,
        read_knowledge_repo,
        read_tool_approval_repo,
        resolved_workflow_repo,
        resolved_incident_repo,
    )


def create_app_container(
    settings: Settings | None = None,
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    model_catalog: ModelCatalogPort | None = None,
    embedding_client: EmbeddingClientPort | None = None,
    incident_repo: IncidentRepositoryPort | None = None,
    pii_scanner: PiiScannerPort | None = None,
    safety_guardrail: SafetyGuardrailPort | None = None,
    *,
    enable_tenant_middleware: bool | None = None,
    enable_opentelemetry: bool | None = None,
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None = None,
    graph_execution_engine: GraphExecutionEngine | None = None,
) -> AppContainer:
    """Build and wire application dependencies into a cohesive container."""
    current_settings = settings or get_settings()

    (
        uow,
        read_repo,
        idempotency_repo,
        audit_repo,
        stream_buffer_repo,
        read_knowledge_repo,
        read_tool_approval_repo,
        resolved_workflow_repo,
        resolved_incident_repo,
    ) = _wire_app_persistence(
        current_settings, unit_of_work, workflow_checkpoint_repo, incident_repo
    )

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

    use_otel = (
        enable_opentelemetry
        if enable_opentelemetry is not None
        else current_settings.ENABLE_OPENTELEMETRY
    )
    if use_otel:
        setup_opentelemetry(service_name=current_settings.OTEL_SERVICE_NAME)

    pii_scanner_adapter = pii_scanner or RegexPiiScannerAdapter()
    safety_guardrail_adapter = safety_guardrail or HeuristicInjectionDetectorAdapter()
    guardrail_pipeline = SafetyGuardrailPipelineService(
        safety_guardrail=safety_guardrail_adapter,
        pii_scanner=pii_scanner_adapter,
    )
    guarded_executor = GuardedCommandExecutor(
        pipeline=guardrail_pipeline,
        incident_repo=resolved_incident_repo,
    )

    fastapi_app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
        idempotent_executor=idempotent_executor,
        stream_recovery_service=stream_recovery_service,
        unit_of_work=uow,
        guarded_executor=guarded_executor,
        incident_repo=resolved_incident_repo,
        enable_tenant_middleware=use_tenant_middleware,
        enable_opentelemetry_middleware=use_otel,
        retriever_service=retriever_service,
        workflow_checkpoint_repo=resolved_workflow_repo,
        graph_execution_engine=graph_execution_engine,
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
        workflow_checkpoint_repo=resolved_workflow_repo,
        graph_execution_engine=graph_execution_engine,
        incident_repo=resolved_incident_repo,
        pii_scanner=pii_scanner_adapter,
        safety_guardrail=safety_guardrail_adapter,
        guardrail_pipeline=guardrail_pipeline,
        guarded_executor=guarded_executor,
    )


# Aliases for naming flexibility
Container = AppContainer
create_container = create_app_container
