"""Physical SQLModel database models for Microsoft SQL Server."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel


class TenantModel(SQLModel, table=True):
    """Physical relational model for the 'tenants' table."""

    __tablename__ = "tenants"  # pyright: ignore[reportAssignmentType]

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    name: str = Field(max_length=200, nullable=False)
    status: str = Field(default="ACTIVE", max_length=20, nullable=False)
    balance_usd: Decimal = Field(
        default=Decimal("0.0000"), max_digits=12, decimal_places=4, nullable=False
    )
    reserved_usd: Decimal = Field(
        default=Decimal("0.0000"), max_digits=12, decimal_places=4, nullable=False
    )
    currency: str = Field(default="USD", max_length=3, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    policy: Optional["TenantPolicyModel"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
            "lazy": "joined",
        },
    )


class TenantPolicyModel(SQLModel, table=True):
    """Physical relational model for the 'tenant_policies' table."""

    __tablename__ = "tenant_policies"  # pyright: ignore[reportAssignmentType]

    tenant_id: str = Field(
        primary_key=True,
        foreign_key="tenants.id",
        max_length=64,
        nullable=False,
        ondelete="CASCADE",
    )
    tier: str = Field(default="FREE", max_length=20, nullable=False)
    max_tokens_per_request: int = Field(default=4096, nullable=False)
    monthly_budget_usd: Decimal = Field(
        default=Decimal("50.0000"), max_digits=12, decimal_places=4, nullable=False
    )
    allowed_models_json: str = Field(
        default='["gpt-4o-mini", "gemini-1.5-flash"]',
        nullable=False,
    )

    tenant: TenantModel | None = Relationship(back_populates="policy")


class ConversationModel(SQLModel, table=True):
    """Physical relational model for the 'conversations' table."""

    __tablename__ = "conversations"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_conversations_tenant_id_id", "tenant_id", "id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    tenant_id: str = Field(default="default-tenant", index=True, max_length=64, nullable=False)
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
    __table_args__ = (Index("ix_audit_logs_tenant_id_id", "tenant_id", "id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    tenant_id: str = Field(default="default-tenant", index=True, max_length=64, nullable=False)
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
    __table_args__ = (Index("ix_stream_buffer_chunks_tenant_id_id", "tenant_id", "id"),)

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    tenant_id: str = Field(default="default-tenant", index=True, max_length=64, nullable=False)
    stream_id: str = Field(max_length=100, index=True, nullable=False)
    sequence_number: int = Field(index=True, nullable=False)
    content: str = Field(nullable=False)
    is_final: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class DocumentModel(SQLModel, table=True):
    """Physical relational model for the 'knowledge_documents' table."""

    __tablename__ = "knowledge_documents"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        Index("ix_knowledge_documents_tenant_id", "tenant_id"),
        Index("ix_knowledge_documents_tenant_status", "tenant_id", "status"),
    )

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    tenant_id: str = Field(
        foreign_key="tenants.id", max_length=64, nullable=False, ondelete="CASCADE"
    )
    filename: str = Field(max_length=255, nullable=False)
    content_type: str = Field(default="text/plain", max_length=100, nullable=False)
    status: str = Field(default="PENDING", max_length=20, nullable=False)
    total_chunks: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    chunks: list["DocumentChunkModel"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "select",
        },
    )


class DocumentChunkModel(SQLModel, table=True):
    """Physical relational model for the 'knowledge_document_chunks' table."""

    __tablename__ = "knowledge_document_chunks"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        Index("ix_knowledge_chunks_tenant_id", "tenant_id"),
        Index("ix_knowledge_chunks_tenant_doc", "tenant_id", "document_id"),
    )

    id: str = Field(primary_key=True, max_length=64, nullable=False)
    tenant_id: str = Field(
        foreign_key="tenants.id", max_length=64, nullable=False, ondelete="CASCADE"
    )
    document_id: str = Field(
        foreign_key="knowledge_documents.id",
        max_length=64,
        nullable=False,
        ondelete="CASCADE",
    )
    sequence_number: int = Field(nullable=False)
    content: str = Field(nullable=False)
    embedding_json: str = Field(nullable=False)
    page_number: int | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    document: DocumentModel | None = Relationship(back_populates="chunks")
