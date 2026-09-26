"""Primary HTTP Adapter (FastAPI) for conversation management and SSE streaming."""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
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
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.domain.shared.domain_error import DomainError
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
) -> None:
    @app.post(
        "/conversations",
        response_model=ConversationResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Conversations"],
        summary="Create a new conversation",
        description="Creates a new conversation aggregate with the provided title.",
    )
    def create_conversation(request: CreateConversationRequest) -> ConversationResponse:
        if create_handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CreateConversationHandler not configured.",
            )
        try:
            result = create_handler.handle(CreateConversationCommand(title=request.title))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return ConversationResponse(id=result.conversation_id, title=result.title)


def _register_message_routes(
    app: FastAPI,
    send_handler: SendMessageHandler | None,
) -> None:
    @app.post(
        "/conversations/{conversation_id}/messages",
        response_model=MessageResponse,
        status_code=status.HTTP_200_OK,
        tags=["Messages"],
        summary="Send a message to a conversation",
        description="Appends a new user message to the specified conversation aggregate.",
    )
    def send_message(
        conversation_id: UUID,
        request: SendMessageRequest,
    ) -> MessageResponse:
        if send_handler is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SendMessageHandler not configured.",
            )
        try:
            result = send_handler.handle(
                SendMessageCommand(conversation_id=conversation_id, content=request.content)
            )
        except ConversationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except (ValueError, DomainError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return MessageResponse(
            conversation_id=result.conversation_id,
            role=result.role,
            content=result.content,
            created_at=result.created_at,
        )


def _register_streaming_routes(
    app: FastAPI,
    stream_handler: StreamConversationQueryHandler | None,
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
    ) -> StreamingResponse:
        if stream_handler is None:
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
    *,
    handler: CreateConversationHandler | None = None,
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

    _register_health_routes(app)
    _register_conversation_routes(app, create_conversation_handler)
    _register_message_routes(app, send_message_handler)
    _register_streaming_routes(app, stream_conversation_handler)

    return app
