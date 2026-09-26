"""
Template canónico para un Value Object en DDD (Domain-Driven Design).
Reglas:
- Inmutable por diseño (@dataclass(frozen=True)).
- Sin identidad propia (igualdad basada en atributos y valores).
- Validación de invariantes de negocio en __post_init__.
- Sin dependencias de frameworks externos.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class MessageValueObject:
    """Representa un mensaje inmutable dentro de una conversación."""

    role: MessageRole
    content: str
    created_at: datetime

    def __post_init__(self) -> None:
        clean_content = self.content.strip() if self.content else ""
        if not clean_content:
            raise ValueError("El contenido del mensaje no puede estar vacío.")
        if len(clean_content) > 4000:
            raise ValueError("El mensaje excede el límite máximo de 4000 caracteres.")

        # Garantizar que created_at tenga zona horaria asignada (UTC por defecto)
        if self.created_at.tzinfo is None:
            object.__setattr__(
                self, "created_at", self.created_at.replace(tzinfo=timezone.utc)
            )

    @classmethod
    def create_user_message(cls, content: str) -> "MessageValueObject":
        return cls(
            role=MessageRole.USER,
            content=content,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def create_assistant_message(cls, content: str) -> "MessageValueObject":
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
