"""Primary HTTP Adapter (FastAPI) for conversation management and SSE streaming."""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.application.agents.services.graph_execution_engine import (
    GraphExecutionEngine,
)
from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageCommand,
    SendMessageHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQuery,
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
from src.application.shared.tenancy.tenant_context import tenant_context
from src.domain.agents.ports.workflow_checkpoint_repository_port import (
    WorkflowCheckpointRepositoryPort,
)
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.conversations.value_objects.message import MessageRole
from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.domain.governance.ports.incident_repository_port import (
    IncidentRepositoryPort,
)
from src.domain.knowledge.value_objects.citation import Citation
from src.domain.shared.domain_error import DomainError
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.messaging.rabbitmq.anyio_document_indexer_worker import (
    AnyioDocumentIndexerWorker,
)
from src.interfaces.http.dependencies.idempotency_dependency import (
    get_optional_idempotency_key,
)
from src.interfaces.http.middlewares.opentelemetry_middleware import (
    OpenTelemetryMiddleware,
)
from src.interfaces.http.middlewares.tenant_context_middleware import (
    TenantContextMiddleware,
)
from src.interfaces.http.resumable_sse_endpoint import (
    build_resumable_sse_response,
)
from src.interfaces.http.routers.approvals_router import (
    create_approvals_router,
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
from src.interfaces.http.schemas import (
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
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
    @app.post(
        "/conversations",
        response_model=ConversationResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Conversations"],
        summary="Create a new conversation",
        description="Creates a new conversation aggregate with the provided title.",
    )
    async def create_conversation(
        request: CreateConversationRequest,
        idempotency_key: Annotated[str | None, Depends(get_optional_idempotency_key)] = None,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ) -> ConversationResponse:
        handler = create_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CreateConversationHandler not configured.",
            )

        async def _execute() -> ConversationResponse:
            tid = TenantId(x_tenant_id or "default-tenant")
            with tenant_context(tid):
                try:
                    res = handler.handle(CreateConversationCommand(title=request.title))
                    return ConversationResponse(id=res.conversation_id, title=res.title)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc

        if idempotent_executor is not None and idempotency_key is not None:
            try:
                return await idempotent_executor.execute(
                    key=idempotency_key,
                    operation=_execute,
                    response_serializer=lambda r: {"id": str(r.id), "title": r.title},
                    response_deserializer=lambda d: ConversationResponse(
                        id=UUID(d["id"]), title=d["title"]
                    ),
                )
            except IdempotencyConflictError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return await _execute()


def _register_message_routes(
    app: FastAPI,
    send_handler: SendMessageHandler | None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
    guarded_executor: GuardedCommandExecutor | None = None,
) -> None:
    @app.post(
        "/conversations/{conversation_id}/messages",
        response_model=MessageResponse,
        status_code=status.HTTP_200_OK,
        tags=["Messages"],
        summary="Send a message to a conversation",
        description="Appends a new user message to the specified conversation aggregate.",
    )
    async def send_message(
        conversation_id: UUID,
        request: SendMessageRequest,
        idempotency_key: Annotated[str | None, Depends(get_optional_idempotency_key)] = None,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ) -> MessageResponse:
        handler = send_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SendMessageHandler not configured.",
            )

        async def _execute_with_text(text: str) -> MessageResponse:
            try:
                res = handler.handle(
                    SendMessageCommand(conversation_id=conversation_id, content=text)
                )
                return MessageResponse(
                    conversation_id=res.conversation_id,
                    role=res.role,
                    content=res.content,
                    created_at=res.created_at,
                )
            except ConversationNotFoundError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
            except (ValueError, DomainError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                ) from exc

        async def _run_command() -> MessageResponse:
            tid = TenantId(x_tenant_id or "default-tenant")
            with tenant_context(tid):
                if guarded_executor is not None:
                    return await guarded_executor.execute_guarded(
                        tenant_id=tid,
                        raw_text=request.content,
                        operation=_execute_with_text,
                    )
                return await _execute_with_text(request.content)

        if idempotent_executor is not None and idempotency_key is not None:
            try:
                return await idempotent_executor.execute(
                    key=idempotency_key,
                    operation=_run_command,
                    response_serializer=lambda r: {
                        "conversation_id": str(r.conversation_id),
                        "role": r.role,
                        "content": r.content,
                        "created_at": r.created_at.isoformat(),
                    },
                    response_deserializer=lambda d: MessageResponse(
                        conversation_id=UUID(d["conversation_id"]),
                        role=d["role"],
                        content=d["content"],
                        created_at=datetime.fromisoformat(d["created_at"]),
                    ),
                )
            except IdempotencyConflictError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return await _run_command()


async def _fetch_streaming_citations(
    retriever_service: HybridRetrieverService | None,
    unit_of_work: UnitOfWork | None,
    conversation_id: UUID,
    tenant_id_str: str | None,
) -> list[Citation]:
    if retriever_service is None or unit_of_work is None:
        return []
    with unit_of_work:
        conv = unit_of_work.conversations.get(conversation_id)
        if conv is None or not conv.messages:
            return []
        user_msg = next((m for m in reversed(conv.messages) if m.role == MessageRole.USER), None)
        query = user_msg.content if user_msg is not None else conv.messages[-1].content
        tid = TenantId(tenant_id_str or "default-tenant")
        return await retriever_service.retrieve_context(
            tenant_id=tid,
            query=query,
            top_k=3,
            min_score=0.1,
        )


def _fetch_streaming_tool_events(
    unit_of_work: UnitOfWork | None,
    conversation_id: UUID,
    tenant_id_str: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    if unit_of_work is None or tenant_id_str is None:
        return []
    events: list[tuple[str, dict[str, Any]]] = []
    tid = TenantId(tenant_id_str)
    with unit_of_work:
        pending_list = unit_of_work.tool_approvals.get_pending(tid)
        for appr in pending_list:
            if appr.conversation_id == str(conversation_id):
                events.append(
                    (
                        "tool_approval_required",
                        {
                            "approval_id": appr.id,
                            "tool_name": appr.tool_call.tool_name,
                            "call_id": appr.tool_call.call_id,
                            "arguments": appr.tool_call.arguments,
                        },
                    )
                )
    return events


async def _sse_event_stream(
    token_iterator: AsyncIterator[str],
    citations: list[Citation],
    tool_events: list[tuple[str, dict[str, Any]]] | None = None,
) -> AsyncIterator[str]:
    try:
        for citation in citations:
            yield f"event: citation\ndata: {json.dumps(citation.to_dict())}\n\n"
        if tool_events:
            for event_name, event_data in tool_events:
                yield f"event: {event_name}\ndata: {json.dumps(event_data)}\n\n"
        async for token in token_iterator:
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: [ERROR] {str(exc)}\n\n"


def _fetch_persisted_assistant_tokens(
    unit_of_work: UnitOfWork | None,
    conversation_id: UUID,
) -> AsyncIterator[str] | None:
    if unit_of_work is None:
        return None
    with unit_of_work as uow:
        conv = uow.conversations.get(conversation_id)
        if not conv or not conv.messages or conv.messages[-1].role != MessageRole.ASSISTANT:
            return None
        content = conv.messages[-1].content

        async def _content_tokens() -> AsyncIterator[str]:
            words = content.split(" ")
            for i, word in enumerate(words):
                yield word if i == len(words) - 1 else f"{word} "

        return _content_tokens()


async def _resolve_assistant_stream_fallback(
    conversation_id: UUID,
    error: DomainError,
    stream_recovery_service: StreamRecoveryService | None = None,
    unit_of_work: UnitOfWork | None = None,
    has_metadata_events: bool = False,
) -> AsyncIterator[str]:
    error_str = str(error).lower()

    if "no messages" in error_str and has_metadata_events:

        async def _empty_tokens() -> AsyncIterator[str]:
            if False:
                yield ""

        return _empty_tokens()

    if "last message is not from user" not in error_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    persisted = _fetch_persisted_assistant_tokens(unit_of_work, conversation_id)
    if persisted is not None:
        return persisted

    if stream_recovery_service is not None:
        tokens = await stream_recovery_service.get_buffered_tokens(str(conversation_id))
        if tokens:

            async def _buffered_tokens() -> AsyncIterator[str]:
                for t in tokens:
                    yield t

            return _buffered_tokens()

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _register_streaming_routes(
    app: FastAPI,
    stream_handler: StreamConversationQueryHandler | None,
    stream_recovery_service: StreamRecoveryService | None = None,
    retriever_service: HybridRetrieverService | None = None,
    unit_of_work: UnitOfWork | None = None,
) -> None:
    @app.get(
        "/conversations/{conversation_id}/stream",
        response_class=StreamingResponse,
        status_code=status.HTTP_200_OK,
        tags=["Streaming"],
        summary="Stream AI conversation response via SSE",
        description="Streams real-time token chunks using Server-Sent Events (SSE).",
    )
    async def stream_conversation(
        conversation_id: UUID,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ) -> StreamingResponse:
        if stream_recovery_service is not None and (
            last_event_id is not None or stream_handler is None
        ):
            return await build_resumable_sse_response(
                stream_id=str(conversation_id),
                recovery_service=stream_recovery_service,
                last_event_id=last_event_id,
            )

        if stream_handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="StreamConversationQueryHandler not configured.",
            )

        citations = await _fetch_streaming_citations(
            retriever_service, unit_of_work, conversation_id, x_tenant_id
        )
        tool_events = _fetch_streaming_tool_events(unit_of_work, conversation_id, x_tenant_id)

        try:
            query = StreamConversationQuery(
                conversation_id=conversation_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            token_iterator = await stream_handler.handle(query)
        except ConversationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except DomainError as exc:
            token_iterator = await _resolve_assistant_stream_fallback(
                conversation_id=conversation_id,
                error=exc,
                stream_recovery_service=stream_recovery_service,
                unit_of_work=unit_of_work,
                has_metadata_events=bool(citations or tool_events),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return StreamingResponse(
            _sse_event_stream(token_iterator, citations, tool_events),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
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
    if create_conversation_handler is None and handler is not None:
        create_conversation_handler = handler

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

    @app.exception_handler(SafetyPolicyViolationError)
    async def safety_policy_violation_handler(
        request: Request, exc: SafetyPolicyViolationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "SafetyPolicyViolation",
                "message": exc.message,
                "violation_type": exc.violation_type,
                "risk_score": exc.risk_score,
                "matched_rule": exc.matched_rule,
                "incident_id": exc.incident_id,
            },
        )

    _register_health_routes(app)
    _register_conversation_routes(app, create_conversation_handler, idempotent_executor)
    _register_message_routes(
        app,
        send_message_handler,
        idempotent_executor,
        guarded_executor=guarded_executor,
    )
    _register_streaming_routes(
        app,
        stream_conversation_handler,
        stream_recovery_service,
        retriever_service=retriever_service,
        unit_of_work=unit_of_work,
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
