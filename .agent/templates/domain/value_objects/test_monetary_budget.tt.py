"""Test template canónico para MonetaryBudget Value Object."""

from decimal import Decimal
import pytest
from .monetary_budget import MonetaryBudget


def test_monetary_budget_initialization_valid() -> None:
    budget = MonetaryBudget(balance=Decimal("100.00"), currency="USD")
    assert budget.balance == Decimal("100.00")
    assert budget.currency == "USD"
    assert budget.reserved_amount == Decimal("0.00")
    assert budget.available_balance == Decimal("100.00")


def test_monetary_budget_negative_balance_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede ser negativo"):
        MonetaryBudget(balance=Decimal("-10.00"))


def test_monetary_budget_reserve_exceeds_balance_raises_error() -> None:
    with pytest.raises(ValueError, match="no puede exceder el saldo total"):
        MonetaryBudget(balance=Decimal("50.00"), reserved_amount=Decimal("60.00"))


def test_monetary_budget_reserve_success() -> None:
    budget = MonetaryBudget(balance=Decimal("100.00"))
    reserved = budget.reserve(Decimal("25.00"))

    assert budget.available_balance == Decimal("100.00")  # Original inmutable
    assert reserved.balance == Decimal("100.00")
    assert reserved.reserved_amount == Decimal("25.00")
    assert reserved.available_balance == Decimal("75.00")


def test_monetary_budget_reserve_insufficient_available_raises_error() -> None:
    budget = MonetaryBudget(balance=Decimal("100.00"), reserved_amount=Decimal("90.00"))
    with pytest.raises(ValueError, match="Saldo insuficiente"):
        budget.reserve(Decimal("15.00"))


def test_monetary_budget_settle_success() -> None:
    budget = MonetaryBudget(balance=Decimal("100.00")).reserve(Decimal("20.00"))
    # Inferencia real costó 18.50 USD
    settled = budget.settle(reserved_cost=Decimal("20.00"), actual_cost=Decimal("18.50"))

    assert settled.balance == Decimal("81.50")
    assert settled.reserved_amount == Decimal("0.00")
    assert settled.available_balance == Decimal("81.50")


def test_monetary_budget_top_up() -> None:
    budget = MonetaryBudget(balance=Decimal("10.00"))
    updated = budget.top_up(Decimal("40.00"))
    assert updated.balance == Decimal("50.00")
