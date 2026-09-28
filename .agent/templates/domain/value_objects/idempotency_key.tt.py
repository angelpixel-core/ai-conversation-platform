"""Template canónico para Value Object IdempotencyKey (DDD).

Reglas:
- Inmutable por diseño (@dataclass(frozen=True)).
- Valida formato no vacío, sin espacios y longitud adecuada (UUID o token hasta 128 chars).
- Sin dependencias de frameworks externos.
"""

from dataclasses import dataclass
import re
import uuid


@dataclass(frozen=True)
class IdempotencyKey:
    """Representa una clave de idempotencia inmutable en el dominio."""

    value: str

    def __post_init__(self) -> None:
        clean = self.value.strip() if self.value else ""
        if not clean:
            raise ValueError("La clave de idempotencia no puede estar vacía.")
        if len(clean) > 128:
            raise ValueError("La clave de idempotencia no puede exceder 128 caracteres.")
        if not re.match(r"^[A-Za-z0-9_\-\.:]+$", clean):
            raise ValueError(
                "La clave de idempotencia contiene caracteres inválidos. Solo se permiten alfanuméricos y -_.:"
            )
        object.__setattr__(self, "value", clean)

    @classmethod
    def generate(cls) -> "IdempotencyKey":
        """Genera una nueva clave de idempotencia basada en UUIDv4."""
        return cls(value=str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
