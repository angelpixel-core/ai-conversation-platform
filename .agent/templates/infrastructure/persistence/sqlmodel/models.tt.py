"""Template canónico para Modelos Relacionales Físicos con SQLModel en Clean Architecture.

Reglas:
- Pertenecen a la capa de Infraestructura (src/infrastructure/persistence/.../models/).
- Las entidades de Dominio NO heredan de SQLModel para mantener desacoplamiento absoluto.
- Define tablas, claves primarias, foráneas, índices y restricciones de base de datos.
- Compatible con dialectos relacionales (Microsoft SQL Server, PostgreSQL, SQLite).
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class ConversationModel(SQLModel, table=True):
    """Modelo relacional físico para la tabla 'conversations'."""

    __tablename__ = "conversations"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    title: str = Field(max_length=200, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relación uno a muchos con mensajes
    messages: list["MessageModel"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class MessageModel(SQLModel, table=True):
    """Modelo relacional físico para la tabla 'messages'."""

    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    conversation_id: UUID = Field(
        foreign_key="conversations.id", index=True, nullable=False, ondelete="CASCADE"
    )
    role: str = Field(max_length=20, nullable=False)
    content: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relación inversa con la conversación
    conversation: Optional[ConversationModel] = Relationship(back_populates="messages")


class OutboxMessageModel(SQLModel, table=True):
    """Modelo relacional físico para la tabla 'outbox_messages' del patrón Outbox."""

    __tablename__ = "outbox_messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    event_type: str = Field(max_length=100, index=True, nullable=False)
    payload: str = Field(nullable=False)  # JSON serializado
    status: str = Field(default="pending", max_length=20, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    processed_at: Optional[datetime] = Field(default=None, nullable=True)
    error_message: Optional[str] = Field(default=None, nullable=True)
