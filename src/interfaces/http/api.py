"""Primary HTTP Adapter (FastAPI) for conversation management and SSE streaming."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.shared.governance.guarded_command_executor import (
    GuardedCommandExecutor,
)
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotencyConflictError,
    IdempotentCommandExecutor,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.domain.governance.ports.incident_repository_port import (
    IncidentRepositoryPort,
)
from src.domain.shared.domain_error import DomainError
from src.infrastructure.messaging.rabbitmq.anyio_document_indexer_worker import (
    AnyioDocumentIndexerWorker,
)
from src.interfaces.http.middlewares.opentelemetry_middleware import (
    OpenTelemetryMiddleware,
)
from src.interfaces.http.middlewares.tenant_context_middleware import (
    TenantContextMiddleware,
)
from src.interfaces.http.problem_details import problem_details_response
from src.interfaces.http.routers.approvals_router import (
    create_approvals_router,
)
from src.interfaces.http.routers.conversations_router import (
    create_conversations_router,
)
from src.interfaces.http.routers.governance_router import (
    create_governance_router,
)
from src.interfaces.http.routers.knowledge_router import (
    create_knowledge_router,
)
from src.interfaces.http.routers.tenant_admin_router import (
    create_tenant_admin_router,
)
from src.interfaces.http.routers.workflows_router import (
    create_workflows_router,
)


def _register_health_routes(app: FastAPI) -> None:
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check endpoint",
        description="Returns current service availability status.",
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}


def _register_conversation_routes(
    app: FastAPI,
    create_handler: CreateConversationHandler | None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
) -> None:
    """Backward-compatible helper to mount conversation creation routes."""
    app.include_router(
        create_conversations_router(
            create_conversation_handler=create_handler,
            idempotent_executor=idempotent_executor,
        )
    )


def _register_message_routes(
    app: FastAPI,
    send_handler: SendMessageHandler | None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
    guarded_executor: GuardedCommandExecutor | None = None,
) -> None:
    """Backward-compatible helper to mount conversation message routes."""
    app.include_router(
        create_conversations_router(
            send_message_handler=send_handler,
            idempotent_executor=idempotent_executor,
            guarded_executor=guarded_executor,
        )
    )


def _register_streaming_routes(
    app: FastAPI,
    stream_handler: StreamConversationQueryHandler | None,
    stream_recovery_service: StreamRecoveryService | None = None,
    retriever_service: HybridRetrieverService | None = None,
    unit_of_work: UnitOfWork | None = None,
) -> None:
    """Backward-compatible helper to mount conversation streaming routes."""
    app.include_router(
        create_conversations_router(
            stream_conversation_handler=stream_handler,
            stream_recovery_service=stream_recovery_service,
            retriever_service=retriever_service,
            unit_of_work=unit_of_work,
        )
    )


TAGS_METADATA = [
    {
        "name": "Health",
        "description": (
            "Liveness and readiness probes verifying API, database, and broker connectivity."
        ),
    },
    {
        "name": "Tenant Administration",
        "description": (
            "Multi-tenant organization provisioning, policy governance, tier enforcement, "
            "and token budget management."
        ),
    },
    {
        "name": "Conversations",
        "description": (
            "Core conversational aggregates, session creation, and lifecycle management."
        ),
    },
    {
        "name": "Messages",
        "description": (
            "User and assistant message dispatching with idempotent deduplication "
            "and real-time security guardrails."
        ),
    },
    {
        "name": "Streaming",
        "description": (
            "Real-time Server-Sent Events (SSE) token generation with sequence replay "
            "and connection recovery."
        ),
    },
    {
        "name": "Knowledge",
        "description": (
            "Enterprise knowledge base ingestion, chunking, and hybrid vector/lexical retrieval "
            "(RAG)."
        ),
    },
    {
        "name": "Approvals",
        "description": (
            "Human-in-the-Loop (HITL) approval workflows gating critical and high-risk "
            "tool executions."
        ),
    },
    {
        "name": "Multi-Agent Workflows",
        "description": (
            "Multi-agent collaborative graph workflows with state snapshots "
            "and immutable checkpointing."
        ),
    },
    {
        "name": "Governance",
        "description": (
            "Audit-grade security guardrails, prompt injection detection, "
            "and PII redaction compliance metrics."
        ),
    },
]


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SafetyPolicyViolationError)
    async def safety_policy_violation_handler(
        request: Request, exc: SafetyPolicyViolationError
    ) -> JSONResponse:
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Safety Policy Violation",
            detail=exc.message,
            type_uri="urn:problem:safety-policy-violation",
            code="PROMPT_INJECTION_DETECTED",
            error="SafetyPolicyViolation",
            message=exc.message,
            violation_type=exc.violation_type,
            risk_score=exc.risk_score,
            matched_rule=exc.matched_rule,
            incident_id=exc.incident_id,
        )

    @app.exception_handler(ConversationNotFoundError)
    async def conversation_not_found_handler(
        request: Request, exc: ConversationNotFoundError
    ) -> JSONResponse:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Conversation Not Found",
            detail=str(exc),
            type_uri="urn:problem:conversation-not-found",
            code="CONVERSATION_NOT_FOUND",
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        request: Request, exc: IdempotencyConflictError
    ) -> JSONResponse:
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            title="Idempotency Conflict",
            detail=str(exc),
            type_uri="urn:problem:idempotency-conflict",
            code="IDEMPOTENCY_CONFLICT",
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Domain Error",
            detail=str(exc),
            type_uri="urn:problem:domain-error",
            code="DOMAIN_INVARIANT_VIOLATION",
        )


def build_api(
    create_conversation_handler: CreateConversationHandler | None = None,
    send_message_handler: SendMessageHandler | None = None,
    stream_conversation_handler: StreamConversationQueryHandler | None = None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
    stream_recovery_service: StreamRecoveryService | None = None,
    unit_of_work: UnitOfWork | None = None,
    guarded_executor: GuardedCommandExecutor | None = None,
    incident_repo: IncidentRepositoryPort | None = None,
    *,
    handler: CreateConversationHandler | None = None,
    enable_tenant_middleware: bool = False,
    enable_opentelemetry_middleware: bool = False,
    retriever_service: HybridRetrieverService | None = None,
    indexer_worker: AnyioDocumentIndexerWorker | None = None,
    workflow_checkpoint_repo: WorkflowCheckpointRepositoryPort | None = None,
    graph_execution_engine: GraphExecutionEngine | None = None,
) -> FastAPI:
    """Create the HTTP adapter around application use cases."""
    active_create_handler = create_conversation_handler or handler

    app = FastAPI(
        title="AI Conversation Platform API",
        description=(
            "### Enterprise AI Conversation Platform\n\n"
            "Production-grade, multi-tenant conversational AI platform built with "
            "Clean Architecture, DDD, CQRS, and Ports & Adapters.\n\n"
            "#### Key Capabilities:\n"
            "- **Multi-Tenancy & Isolation:** Context propagation via `X-Tenant-Id` header.\n"
            "- **Idempotency Guarantees:** Zero-duplicate message delivery via "
            "`Idempotency-Key` (UUIDv4).\n"
            "- **Real-Time Streaming:** Resilient SSE streaming with sequence recovery "
            "(`Last-Event-ID`).\n"
            "- **Human-in-the-Loop:** Sensitive tool execution gated by administrative "
            "approval workflows.\n"
            "- **Hybrid RAG:** Dense vector embeddings + lexical search with source citations.\n"
            "- **Multi-Agent Systems:** State graph orchestrations with versioned "
            "state checkpoints.\n"
            "- **AI Governance:** Real-time prompt injection blocking, PII masking, "
            "and distributed tracing."
        ),
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if enable_opentelemetry_middleware:
        app.add_middleware(OpenTelemetryMiddleware)

    if enable_tenant_middleware:
        app.add_middleware(TenantContextMiddleware)

    _register_exception_handlers(app)
    _register_health_routes(app)
    app.include_router(
        create_conversations_router(
            create_conversation_handler=active_create_handler,
            send_message_handler=send_message_handler,
            stream_conversation_handler=stream_conversation_handler,
            idempotent_executor=idempotent_executor,
            stream_recovery_service=stream_recovery_service,
            retriever_service=retriever_service,
            unit_of_work=unit_of_work,
            guarded_executor=guarded_executor,
        )
    )

    if incident_repo is not None:
        app.include_router(create_governance_router(incident_repo))

    if unit_of_work is not None:
        app.include_router(create_tenant_admin_router(unit_of_work))
        app.include_router(create_knowledge_router(unit_of_work, indexer_worker=indexer_worker))
        app.include_router(create_approvals_router(unit_of_work))

    if workflow_checkpoint_repo is not None:
        app.include_router(
            create_workflows_router(
                checkpoint_repo=workflow_checkpoint_repo,
                execution_engine=graph_execution_engine,
            )
        )

    return app


__all__ = [
    "TAGS_METADATA",
    "build_api",
]
