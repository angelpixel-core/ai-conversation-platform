"""Test template canónico para ModelRoute Value Object."""

from decimal import Decimal
import pytest
from .model_route import ModelRoute


def test_model_route_valid_creation() -> None:
    route = ModelRoute(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_tokens=Decimal("0.00015"),
        cost_per_1k_output_tokens=Decimal("0.00060"),
        fallback_model_id="gemini-1.5-flash",
    )
    assert route.provider == "openai"
    assert route.model_name == "gpt-4o-mini"
    assert route.fallback_model_id == "gemini-1.5-flash"


def test_model_route_empty_provider_raises_error() -> None:
    with pytest.raises(ValueError, match="proveedor del modelo no puede estar vacío"):
        ModelRoute(
            provider="   ",
            model_name="gpt-4o",
            cost_per_1k_input_tokens=Decimal("0.005"),
            cost_per_1k_output_tokens=Decimal("0.015"),
        )


def test_model_route_estimate_cost() -> None:
    route = ModelRoute(
        provider="openai",
        model_name="test-model",
        cost_per_1k_input_tokens=Decimal("0.01"),  # 0.01 USD / 1k in
        cost_per_1k_output_tokens=Decimal("0.03"), # 0.03 USD / 1k out
    )
    # 2000 in (0.02) + 1000 out (0.03) = 0.05
    cost = route.estimate_cost(prompt_tokens=2000, estimated_output_tokens=1000)
    assert cost == Decimal("0.0500")
