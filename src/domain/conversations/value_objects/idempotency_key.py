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

from src.domain.conversations.exceptions import InvalidUuidFormatError

UUID_V4_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


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

    @classmethod
    def from_raw(cls, raw: str) -> "IdempotencyKey":
        """Semantic factory method creating IdempotencyKey from raw string."""
        return cls(value=raw)

    @classmethod
    def create(cls, key: str) -> "IdempotencyKey":
        """Semantic factory method creating IdempotencyKey."""
        return cls(value=key)

    @classmethod
    def from_uuid_v4(cls, raw: str) -> "IdempotencyKey":
        """Validate and create an IdempotencyKey strictly conforming to RFC 4122 UUIDv4.

        Args:
            raw: Raw string representation of the UUIDv4 header.

        Returns:
            Validated IdempotencyKey instance with normalized lowercase UUIDv4 string.

        Raises:
            InvalidUuidFormatError: If raw string is empty or not a valid RFC 4122 UUIDv4.
        """
        clean = raw.strip() if raw else ""
        if not clean or not UUID_V4_REGEX.match(clean):
            raise InvalidUuidFormatError(
                f"El encabezado 'X-Idempotency-Key' debe ser un UUIDv4 válido (RFC 4122): '{raw}'."
            )
        return cls(value=clean.lower())

    def __str__(self) -> str:
        return self.value
