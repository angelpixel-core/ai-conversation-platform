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
