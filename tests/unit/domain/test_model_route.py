"""Unit tests for ModelRoute value object."""

from decimal import Decimal

import pytest

from src.domain.routing.value_objects.model_route import ModelRoute


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
    assert route.max_context_tokens == 8192
    assert route.tier_required == "FREE"


def test_model_route_empty_provider_raises_error() -> None:
    with pytest.raises(ValueError, match="proveedor del modelo no puede estar vacío"):
        ModelRoute(
            provider="   ",
            model_name="gpt-4o",
            cost_per_1k_input_tokens=Decimal("0.005"),
            cost_per_1k_output_tokens=Decimal("0.015"),
        )


def test_model_route_empty_model_name_raises_error() -> None:
    with pytest.raises(ValueError, match="nombre del modelo no puede estar vacío"):
        ModelRoute(
            provider="openai",
            model_name="   ",
            cost_per_1k_input_tokens=Decimal("0.005"),
            cost_per_1k_output_tokens=Decimal("0.015"),
        )


def test_model_route_negative_cost_raises_error() -> None:
    with pytest.raises(ValueError, match="coste de tokens de entrada no puede ser negativo"):
        ModelRoute(
            provider="openai",
            model_name="gpt-4o",
            cost_per_1k_input_tokens=Decimal("-0.01"),
            cost_per_1k_output_tokens=Decimal("0.01"),
        )


def test_model_route_invalid_context_tokens_raises_error() -> None:
    with pytest.raises(ValueError, match="ventana de contexto debe ser un entero positivo"):
        ModelRoute(
            provider="openai",
            model_name="gpt-4o",
            cost_per_1k_input_tokens=Decimal("0.01"),
            cost_per_1k_output_tokens=Decimal("0.01"),
            max_context_tokens=0,
        )


def test_model_route_estimate_cost() -> None:
    route = ModelRoute(
        provider="openai",
        model_name="test-model",
        cost_per_1k_input_tokens=Decimal("0.01"),  # 0.01 USD / 1k in
        cost_per_1k_output_tokens=Decimal("0.03"),  # 0.03 USD / 1k out
    )
    # 2000 in (0.02) + 1000 out (0.03) = 0.05
    cost = route.estimate_cost(prompt_tokens=2000, estimated_output_tokens=1000)
    assert cost == Decimal("0.0500")


def test_model_route_immutability() -> None:
    route = ModelRoute(
        provider="openai",
        model_name="gpt-4o",
        cost_per_1k_input_tokens=Decimal("0.005"),
        cost_per_1k_output_tokens=Decimal("0.015"),
    )
    with pytest.raises(AttributeError):
        route.model_name = "other-model"  # type: ignore[misc]
