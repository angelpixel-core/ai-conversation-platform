# Step 01 - Primary Adapter / Driver

from fastapi import FastAPI, HTTPException

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from src.interfaces.http.schemas import ConversationResponse, CreateConversationRequest


def build_api(handler: CreateConversationHandler) -> FastAPI:
    """Create the HTTP adapter around application use cases."""

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

    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check endpoint",
        description="Returns current service availability status.",
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/conversations",
        response_model=ConversationResponse,
        status_code=201,
        tags=["Conversations"],
        summary="Create a new conversation",
        description=(
            "Creates a new conversation aggregate with the provided title and assigns a unique ID."
        ),
    )
    def create_conversation(
        request: CreateConversationRequest,
    ) -> ConversationResponse:
        try:
            result = handler.handle(CreateConversationCommand(title=request.title))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return ConversationResponse(
            id=result.conversation_id,
            title=result.title,
        )

    return app
