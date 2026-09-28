"""Template canónico para Value Object ModelRoute (DDD).

Reglas:
- Inmutable por diseño (@dataclass(frozen=True)).
- Modela la ruta de inferencia de un modelo LLM con sus costos por token y modelo de contingencia.
- Sin dependencias de frameworks externos.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ModelRoute:
    """Representa una ruta de inferencia asignada a un inquilino o prompt."""

    provider: str
    model_name: str
    cost_per_1k_input_tokens: Decimal
    cost_per_1k_output_tokens: Decimal
    fallback_model_id: Optional[str] = None
    max_context_tokens: int = 8192
    tier_required: str = "FREE"

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("El proveedor del modelo no puede estar vacío.")
        if not self.model_name.strip():
            raise ValueError("El nombre del modelo no puede estar vacío.")
        if self.cost_per_1k_input_tokens < Decimal("0.00"):
            raise ValueError("El coste de tokens de entrada no puede ser negativo.")
        if self.cost_per_1k_output_tokens < Decimal("0.00"):
            raise ValueError("El coste de tokens de salida no puede ser negativo.")
        if self.max_context_tokens <= 0:
            raise ValueError("La ventana de contexto debe ser un entero positivo.")

    def estimate_cost(self, prompt_tokens: int, estimated_output_tokens: int) -> Decimal:
        """Calcula el costo estimado en base al volumen proyectado de tokens."""
        input_cost = (Decimal(str(prompt_tokens)) / Decimal("1000")) * self.cost_per_1k_input_tokens
        output_cost = (Decimal(str(estimated_output_tokens)) / Decimal("1000")) * self.cost_per_1k_output_tokens
        return (input_cost + output_cost).quantize(Decimal("0.0001"))
