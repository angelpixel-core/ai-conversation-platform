"""ModelRoute value object representing LLM model routing and pricing specifications."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ModelRoute:
    """Represents an LLM model routing policy with token costs and fallback."""

    provider: str
    model_name: str
    cost_per_1k_input_tokens: Decimal
    cost_per_1k_output_tokens: Decimal
    fallback_model_id: str | None = None
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
        """Estimates total cost based on projected input and output token counts."""
        input_cost = (Decimal(str(prompt_tokens)) / Decimal("1000")) * self.cost_per_1k_input_tokens
        output_cost = (
            Decimal(str(estimated_output_tokens)) / Decimal("1000")
        ) * self.cost_per_1k_output_tokens
        return (input_cost + output_cost).quantize(Decimal("0.0001"))
