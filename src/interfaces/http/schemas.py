"""Pydantic v2 DTO schemas for Conversation and Message HTTP endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.interfaces.http.problem_details import (
    ProblemDetails,
    problem_details_response,
)


class CreateConversationRequest(BaseModel):
    """Payload to create a new conversational session."""

    title: str = Field(
        min_length=1,
        max_length=200,
        description="Human-readable title or subject for the conversation aggregate.",
        examples=["Project Architecture Discussion"],
    )


class ConversationResponse(BaseModel):
    """Schema representing an existing conversation aggregate."""

    id: UUID = Field(
        description="Unique identifier (UUIDv4) of the conversation aggregate.",
    )
    title: str = Field(
        description="Title of the conversation.",
        examples=["Project Architecture Discussion"],
    )


class SendMessageRequest(BaseModel):
    """Payload to append a message to an existing conversation."""

    content: str = Field(
        min_length=1,
        max_length=10000,
        description="Raw message text content submitted by the user.",
        examples=["Could you summarize the Q3 financial report?"],
    )


class MessageResponse(BaseModel):
    """Schema representing an appended conversation message."""

    conversation_id: UUID = Field(
        description="Unique identifier of the owning conversation.",
    )
    role: str = Field(
        description="Message role within the conversation (user, assistant, system, tool).",
        examples=["user", "assistant"],
    )
    content: str = Field(
        description="Textual content of the message.",
    )
    created_at: datetime = Field(
        description="UTC timestamp when the message was recorded.",
    )


__all__ = [
    "ConversationResponse",
    "CreateConversationRequest",
    "MessageResponse",
    "ProblemDetails",
    "SendMessageRequest",
    "problem_details_response",
]
