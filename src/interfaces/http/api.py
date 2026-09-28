"""Primary HTTP Adapter (FastAPI) for conversation management and SSE streaming."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import StreamingResponse

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
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotencyConflictError,
    IdempotentCommandExecutor,
)
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.shared.domain_error import DomainError
from src.interfaces.http.dependencies.idempotency_dependency import (
    get_optional_idempotency_key,
)
from src.interfaces.http.middlewares.tenant_context_middleware import (
    TenantContextMiddleware,
)
from src.interfaces.http.resumable_sse_endpoint import (
    build_resumable_sse_response,
)
from src.interfaces.http.routers.tenant_admin_router import (
    create_tenant_admin_router,
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
    ) -> ConversationResponse:
        handler = create_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CreateConversationHandler not configured.",
            )

        async def _execute() -> ConversationResponse:
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
    ) -> MessageResponse:
        handler = send_handler
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SendMessageHandler not configured.",
            )

        async def _execute() -> MessageResponse:
            try:
                res = handler.handle(
                    SendMessageCommand(conversation_id=conversation_id, content=request.content)
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

        if idempotent_executor is not None and idempotency_key is not None:
            try:
                return await idempotent_executor.execute(
                    key=idempotency_key,
                    operation=_execute,
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

        return await _execute()


def _register_streaming_routes(
    app: FastAPI,
    stream_handler: StreamConversationQueryHandler | None,
    stream_recovery_service: StreamRecoveryService | None = None,
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
    ) -> StreamingResponse:
        if last_event_id is not None and stream_recovery_service is not None:
            return await build_resumable_sse_response(
                stream_id=str(conversation_id),
                recovery_service=stream_recovery_service,
                last_event_id=last_event_id,
            )

        if stream_handler is None:
            if stream_recovery_service is not None:
                return await build_resumable_sse_response(
                    stream_id=str(conversation_id),
                    recovery_service=stream_recovery_service,
                    last_event_id=last_event_id,
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="StreamConversationQueryHandler not configured.",
            )

        try:
            query = StreamConversationQuery(
                conversation_id=conversation_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            token_iterator = await stream_handler.handle(query)
        except ConversationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except (ValueError, DomainError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        async def sse_event_generator() -> AsyncIterator[str]:
            try:
                async for token in token_iterator:
                    yield f"data: {token}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                yield f"data: [ERROR] {str(exc)}\n\n"

        return StreamingResponse(
            sse_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


def build_api(
    create_conversation_handler: CreateConversationHandler | None = None,
    send_message_handler: SendMessageHandler | None = None,
    stream_conversation_handler: StreamConversationQueryHandler | None = None,
    idempotent_executor: IdempotentCommandExecutor | None = None,
    stream_recovery_service: StreamRecoveryService | None = None,
    unit_of_work: UnitOfWork | None = None,
    *,
    handler: CreateConversationHandler | None = None,
    enable_tenant_middleware: bool = False,
) -> FastAPI:
    """Create the HTTP adapter around application use cases."""
    if create_conversation_handler is None and handler is not None:
        create_conversation_handler = handler

    app = FastAPI(
        title="AI Conversation Platform API",
        description=(
            "Core API service for managing AI-driven conversations, messages, and RAG contexts."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if enable_tenant_middleware:
        app.add_middleware(TenantContextMiddleware)

    _register_health_routes(app)
    _register_conversation_routes(app, create_conversation_handler, idempotent_executor)
    _register_message_routes(app, send_message_handler, idempotent_executor)
    _register_streaming_routes(app, stream_conversation_handler, stream_recovery_service)

    if unit_of_work is not None:
        app.include_router(create_tenant_admin_router(unit_of_work))

    return app
