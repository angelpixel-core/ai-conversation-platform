# Step 01 - Primary Adapter / Driver

from fastapi import FastAPI, HTTPException

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from src.interfaces.http.schemas import ConversationResponse, CreateConversationRequest


def build_api(handler: CreateConversationHandler) -> FastAPI:
    """Create the HTTP adapter around application use cases."""

    app = FastAPI(title="AI Conversation Platform", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/conversations",
        response_model=ConversationResponse,
        status_code=201,
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
