"""Message Value Object in the Conversations domain."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MessageRole(StrEnum):
    """Supported roles in conversation turns."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Message:
    """Immutable Message Value Object representing a single conversation turn."""

    role: MessageRole
    content: str
    created_at: datetime
    id: UUID = field(default_factory=uuid4, compare=False)
    idempotency_key: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        clean_content = self.content.strip() if self.content else ""
        if not clean_content:
            raise ValueError("El contenido del mensaje no puede estar vacío.")

        if len(clean_content) > 4000:
            raise ValueError("El mensaje excede el límite máximo de 4000 caracteres.")

        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=UTC))

    @classmethod
    def create_user_message(
        cls,
        content: str,
        idempotency_key: str | None = None,
    ) -> "Message":
        """Factory method for user messages."""
        return cls(
            role=MessageRole.USER,
            content=content,
            created_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )

    @classmethod
    def create_assistant_message(
        cls,
        content: str,
        idempotency_key: str | None = None,
    ) -> "Message":
        """Factory method for assistant messages."""
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )

    @classmethod
    def create_system_message(cls, content: str) -> "Message":
        """Factory method for system messages."""
        return cls(
            role=MessageRole.SYSTEM,
            content=content,
            created_at=datetime.now(UTC),
        )
