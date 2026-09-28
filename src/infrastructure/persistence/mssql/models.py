"""Physical SQLModel database models for Microsoft SQL Server."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class ConversationModel(SQLModel, table=True):
    """Physical relational model for the 'conversations' table."""

    __tablename__ = "conversations"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    title: str = Field(max_length=200, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    messages: list["MessageModel"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class MessageModel(SQLModel, table=True):
    """Physical relational model for the 'messages' table."""

    __tablename__ = "messages"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    conversation_id: UUID = Field(
        foreign_key="conversations.id", index=True, nullable=False, ondelete="CASCADE"
    )
    role: str = Field(max_length=20, nullable=False)
    content: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    conversation: ConversationModel | None = Relationship(back_populates="messages")


class OutboxMessageModel(SQLModel, table=True):
    """Physical relational model for the 'outbox_messages' table."""

    __tablename__ = "outbox_messages"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    event_type: str = Field(max_length=100, index=True, nullable=False)
    payload: str = Field(nullable=False)
    status: str = Field(default="pending", max_length=20, index=True, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    processed_at: datetime | None = Field(default=None, nullable=True)
    error_message: str | None = Field(default=None, nullable=True)


class IdempotencyRecordModel(SQLModel, table=True):
    """Physical relational model for the 'idempotency_keys' table."""

    __tablename__ = "idempotency_keys"  # pyright: ignore[reportAssignmentType]

    key: str = Field(primary_key=True, max_length=255, nullable=False)
    status: str = Field(max_length=20, index=True, nullable=False)
    response_code: int | None = Field(default=None, nullable=True)
    response_body: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class AuditLogModel(SQLModel, table=True):
    """Physical relational model for the 'audit_logs' table."""

    __tablename__ = "audit_logs"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    event_name: str = Field(max_length=100, index=True, nullable=False)
    actor_id: str = Field(max_length=100, index=True, nullable=False)
    resource_type: str = Field(max_length=50, index=True, nullable=False)
    resource_id: str = Field(max_length=100, index=True, nullable=False)
    action: str = Field(max_length=50, nullable=False)
    tokens_consumed: int = Field(default=0, nullable=False)
    payload_json: str | None = Field(default=None, nullable=True)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class StreamBufferChunkModel(SQLModel, table=True):
    """Physical relational model for the 'stream_buffer_chunks' table."""

    __tablename__ = "stream_buffer_chunks"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    stream_id: str = Field(max_length=100, index=True, nullable=False)
    sequence_number: int = Field(index=True, nullable=False)
    content: str = Field(nullable=False)
    is_final: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
