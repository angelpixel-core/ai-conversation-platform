"""Unit tests verifying semantic factory methods and immutability across domain Value Objects."""

from decimal import Decimal

from src.domain.agents.value_objects.checkpoint_id import CheckpointId
from src.domain.agents.value_objects.workflow_id import WorkflowId
from src.domain.conversations.value_objects.idempotency_key import IdempotencyKey
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


def test_tenant_id_semantic_factories() -> None:
    t1 = TenantId.from_raw("org-alpha")
    t2 = TenantId.create("org-alpha")
    assert t1 == t2
    assert str(t1) == "org-alpha"
    assert t1.value == "org-alpha"


def test_monetary_budget_semantic_factories() -> None:
    zero_usd = MonetaryBudget.zero()
    assert zero_usd.balance == Decimal("0.00")
    assert zero_usd.currency == "USD"
    assert zero_usd.reserved_amount == Decimal("0.00")
    assert zero_usd.available_balance == Decimal("0.00")

    zero_eur = MonetaryBudget.zero(currency="EUR")
    assert zero_eur.currency == "EUR"

    custom = MonetaryBudget.create(balance="150.50", currency="USD", reserved_amount="25.00")
    assert custom.balance == Decimal("150.50")
    assert custom.reserved_amount == Decimal("25.00")
    assert custom.available_balance == Decimal("125.50")


def test_idempotency_key_semantic_factories() -> None:
    k1 = IdempotencyKey.from_raw("idemp-key-1234")
    k2 = IdempotencyKey.create("idemp-key-1234")
    assert k1 == k2
    assert str(k1) == "idemp-key-1234"

    generated = IdempotencyKey.generate()
    assert isinstance(generated, IdempotencyKey)
    assert len(generated.value) > 10


def test_workflow_and_checkpoint_id_semantic_factories() -> None:
    w1 = WorkflowId.from_raw("wf-abc")
    w2 = WorkflowId.create("wf-abc")
    assert w1 == w2
    assert str(w1) == "wf-abc"

    c1 = CheckpointId.from_raw("chk-123")
    c2 = CheckpointId.create("chk-123")
    assert c1 == c2
    assert str(c1) == "chk-123"
