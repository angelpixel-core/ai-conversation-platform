"""Pydantic v2 DTO schemas for Conversation and Message HTTP endpoints (RFC-33)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

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
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional client metadata (channel, user_id, etc.).",
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
    tenant_id: str = Field(
        default="default-tenant",
        description="Owning tenant identifier.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the conversation was created.",
    )
    status: str = Field(
        default="ACTIVE",
        description="Lifecycle status of the conversation.",
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
    """Schema representing an appended conversation message (RFC-33)."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier of the persisted message.",
    )
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
    idempotency_key: str | None = Field(
        default=None,
        description="Client-supplied idempotency key (UUIDv4) associated with this message.",
    )
    created_at: datetime = Field(
        description="UTC timestamp when the message was recorded.",
    )
    cached: bool = Field(
        default=False,
        description="True when the response was replayed from idempotency cache.",
    )


class ConversationMessageItemResponse(BaseModel):
    """Schema representing an individual message inside GET /conversations/{id}."""

    id: str = Field(
        description="Unique message identifier.",
    )
    role: str = Field(
        description="Message role (user, assistant, system).",
    )
    content: str = Field(
        description="Message text content.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key correlated with the message turn.",
    )
    created_at: datetime = Field(
        description="UTC timestamp when the message was created.",
    )
    delivery_status: str = Field(
        default="DELIVERED",
        description="Delivery status of the message.",
    )


class ConversationHistoryResponse(BaseModel):
    """Schema returned by GET /conversations/{conversation_id} (RFC-33)."""

    id: UUID = Field(
        description="Unique conversation identifier.",
    )
    title: str = Field(
        description="Title of the conversation.",
    )
    tenant_id: str = Field(
        description="Owning tenant identifier.",
    )
    created_at: datetime = Field(
        description="UTC creation timestamp of the conversation.",
    )
    can_append_user_message: bool = Field(
        description="Whether the turn state allows the user to append a new message.",
    )
    messages: list[ConversationMessageItemResponse] = Field(
        default_factory=list,
        description="Ordered history of messages in the conversation.",
    )


__all__ = [
    "ConversationHistoryResponse",
    "ConversationMessageItemResponse",
    "ConversationResponse",
    "CreateConversationRequest",
    "MessageResponse",
    "ProblemDetails",
    "SendMessageRequest",
    "problem_details_response",
]
