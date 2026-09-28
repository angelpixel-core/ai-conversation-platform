"""Value Object for Idempotency Key in DDD.

Rules:
- Immutable by design (@dataclass(frozen=True)).
- Validates non-empty, stripped format, alphanumeric and safe symbols (-_.:).
- Max length limit (128 characters).
- Zero external framework dependencies (standard library only).
"""

import re
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class IdempotencyKey:
    """Represents an immutable idempotency key in the domain."""

    value: str

    def __post_init__(self) -> None:
        clean = self.value.strip() if self.value else ""
        if not clean:
            raise ValueError("La clave de idempotencia no puede estar vacía.")
        if len(clean) > 128:
            raise ValueError("La clave de idempotencia no puede exceder 128 caracteres.")
        if not re.match(r"^[A-Za-z0-9_\-\.:]+$", clean):
            raise ValueError(
                "La clave de idempotencia contiene caracteres inválidos. "
                "Solo se permiten alfanuméricos y -_.:"
            )
        object.__setattr__(self, "value", clean)

    @classmethod
    def generate(cls) -> "IdempotencyKey":
        """Generate a random UUIDv4-based idempotency key."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
