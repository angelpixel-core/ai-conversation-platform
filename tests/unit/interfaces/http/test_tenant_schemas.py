"""Unit tests for Pydantic v2 tenant administration schemas and RFC-32 contract."""

import pytest

from src.interfaces.http.tenant_schemas import (
    CreateTenantRequest,
    ReserveQuotaRequest,
    ReserveQuotaResponse,
    TenantBudgetResponse,
    TenantFinancialsSchema,
    TenantLimitsSchema,
    TenantMetadataSchema,
    TenantPolicyResponse,
    TenantSummaryResponse,
    UpdateTenantPolicyRequest,
)


def test_create_tenant_request_resolves_id_or_tenant_id() -> None:
    """Verify CreateTenantRequest accepts id or tenant_id interchangeably."""
    req_canonical = CreateTenantRequest(
        id="canonical-slug",
        name="Canonical Corp",
    )
    assert req_canonical.resolved_id == "canonical-slug"

    req_alias = CreateTenantRequest(
        tenant_id="alias-slug",
        name="Alias Corp",
    )
    assert req_alias.resolved_id == "alias-slug"

    req_both = CreateTenantRequest(
        id="primary-slug",
        tenant_id="fallback-slug",
        name="Dual Corp",
    )
    assert req_both.resolved_id == "primary-slug"

    req_empty = CreateTenantRequest(name="Empty Slug Corp")
    with pytest.raises(ValueError, match="obligatorio"):
        _ = req_empty.resolved_id


def test_tenant_summary_response_serialization_rfc32() -> None:
    """Verify TenantSummaryResponse serialization matches RFC-32 dual format."""
    summary = TenantSummaryResponse(
        id="corp-acme",
        tenant_id="corp-acme",
        name="ACME Corporation",
        status="ACTIVE",
        tier="ENTERPRISE",
        balance="1000.0000",
        reserved_amount="0.0000",
        available_balance="1000.0000",
        currency="USD",
        financials=TenantFinancialsSchema(
            currency="USD",
            balance="1000.0000",
            reserved_amount="0.0000",
            available_balance="1000.0000",
            monthly_budget_usd="500.0000",
        ),
        limits=TenantLimitsSchema(
            max_tokens_per_request=16384,
            max_requests_per_minute=120,
        ),
        metadata=TenantMetadataSchema(
            created_at="2026-09-15T10:00:00Z",
            updated_at="2026-10-15T11:30:00Z",
            contact_email="ops@acme.corp",
        ),
    )

    data = summary.model_dump()
    assert data["id"] == "corp-acme"
    assert data["tenant_id"] == "corp-acme"
    assert data["balance"] == "1000.0000"
    assert data["financials"]["monthly_budget_usd"] == "500.0000"
    assert data["limits"]["max_tokens_per_request"] == 16384
    assert data["metadata"]["contact_email"] == "ops@acme.corp"


def test_tenant_budget_and_policy_responses_expose_dual_ids() -> None:
    """Verify budget and policy responses expose id and tenant_id."""
    budget = TenantBudgetResponse(
        id="corp-test",
        tenant_id="corp-test",
        balance="100.0000",
        reserved_amount="10.0000",
        available_balance="90.0000",
        currency="USD",
    )
    assert budget.id == "corp-test"
    assert budget.tenant_id == "corp-test"

    policy = TenantPolicyResponse(
        id="corp-test",
        tenant_id="corp-test",
        tier="PRO",
        max_tokens_per_request=8192,
        monthly_budget_usd="2000.0000",
        max_requests_per_minute=120,
        allowed_models=["gpt-4o", "claude-3-5-sonnet"],
    )
    assert policy.id == "corp-test"
    assert policy.tenant_id == "corp-test"
    assert policy.tier == "PRO"


def test_update_tenant_policy_request_schema() -> None:
    """Verify UpdateTenantPolicyRequest validation and serialization."""
    req = UpdateTenantPolicyRequest(
        tier="PRO",
        max_tokens_per_request=8192,
        monthly_budget_usd="1500.00",
        max_requests_per_minute=100,
        allowed_models=["gpt-4o"],
    )
    assert req.tier == "PRO"
    assert req.max_tokens_per_request == 8192
    assert req.monthly_budget_usd == "1500.00"
    assert req.max_requests_per_minute == 100
    assert req.allowed_models == ["gpt-4o"]


def test_reserve_quota_request_and_response() -> None:
    """Verify ReserveQuotaRequest and ReserveQuotaResponse RFC-32 dual format."""
    req = ReserveQuotaRequest(
        estimated_cost="0.0500",
        model_id="gpt-4o",
    )
    assert req.estimated_cost == "0.0500"
    assert req.model_id == "gpt-4o"

    res = ReserveQuotaResponse(
        id="corp-test",
        tenant_id="corp-test",
        reserved_cost="0.0500",
        remaining_balance="99.9500",
    )
    assert res.id == "corp-test"
    assert res.tenant_id == "corp-test"
    assert res.reserved_cost == "0.0500"
    assert res.remaining_balance == "99.9500"
