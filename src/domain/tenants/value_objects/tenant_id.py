"""TenantId value object representing an immutable tenant identifier."""

import re
from dataclasses import dataclass

from src.domain.tenants.exceptions import TenantValidationError


@dataclass(frozen=True)
class TenantId:
    """Represents an immutable unique tenant identifier."""

    value: str

    def __post_init__(self) -> None:
        clean = self.value.strip().lower() if self.value else ""
        if not clean:
            raise TenantValidationError("El identificador del tenant no puede estar vacío.")
        if len(clean) < 3 or len(clean) > 64:
            raise TenantValidationError(
                "El identificador del tenant debe tener entre 3 y 64 caracteres. "
                f"Longitud actual: {len(clean)}"
            )
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", clean):
            raise TenantValidationError(
                f"El identificador '{clean}' contiene caracteres inválidos. "
                "Debe ser un slug alfanumérico en minúsculas separado por guiones."
            )
        object.__setattr__(self, "value", clean)

    @classmethod
    def from_raw(cls, raw: str) -> "TenantId":
        """Semantic factory method creating TenantId from raw string representation.

        Args:
            raw: Raw tenant identifier string.

        Returns:
            Validated immutable TenantId instance.
        """
        return cls(value=raw)

    @classmethod
    def create(cls, slug: str) -> "TenantId":
        """Semantic factory alias for creating a TenantId.

        Args:
            slug: Alphanumeric hyphen-separated slug string.

        Returns:
            Validated immutable TenantId instance.
        """
        return cls(value=slug)

    def __str__(self) -> str:
        return self.value
