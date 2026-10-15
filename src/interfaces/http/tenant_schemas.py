"""Pydantic v2 DTO schemas for tenant administration and multi-tenant isolation."""

from pydantic import BaseModel, ConfigDict, Field


class TenantFinancialsSchema(BaseModel):
    """Detailed financial balances and limits for a tenant."""

    model_config = ConfigDict(frozen=True)

    currency: str = Field(default="USD", max_length=3, description="Currency denomination")
    balance: str = Field(..., description="Total allocated budget balance")
    reserved_amount: str = Field(default="0.0000", description="Active in-flight reserved amount")
    available_balance: str = Field(..., description="Net remaining available budget")
    monthly_budget_usd: str = Field(..., description="Monthly spending ceiling")


class TenantLimitsSchema(BaseModel):
    """Operational rate and token limits for a tenant."""

    model_config = ConfigDict(frozen=True)

    max_tokens_per_request: int = Field(default=4096, description="Token ceiling per request")
    max_requests_per_minute: int = Field(default=60, description="RPM rate limit ceiling")


class TenantMetadataSchema(BaseModel):
    """Audit and administrative metadata for a tenant."""

    model_config = ConfigDict(frozen=True)

    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC modification timestamp")
    contact_email: str | None = Field(default=None, description="Operations contact email")


class TenantSummaryResponse(BaseModel):
    """Unified tenant summary response conforming to RFC-32 specifications.

    Exposes canonical 'id' and legacy alias 'tenant_id', root flattened financial
    fields for backwards compatibility, and nested RFC-32 structured sub-objects.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Canonical tenant identifier slug")
    tenant_id: str = Field(..., description="Alias tenant identifier for backward compatibility")
    name: str = Field(..., description="Organization display name")
    status: str = Field(..., description="Operational status (ACTIVE, SUSPENDED)")
    tier: str = Field(..., description="Service tier (FREE, STANDARD, PRO, ENTERPRISE)")
    balance: str = Field(..., description="Current budget balance (flattened)")
    reserved_amount: str = Field(..., description="Reserved amount (flattened)")
    available_balance: str = Field(..., description="Available balance (flattened)")
    currency: str = Field(..., description="Budget currency code")
    financials: TenantFinancialsSchema = Field(..., description="Financial details breakdown")
    limits: TenantLimitsSchema = Field(..., description="Operational limits breakdown")
    metadata: TenantMetadataSchema = Field(..., description="Administrative metadata")


class CreateTenantRequest(BaseModel):
    """Schema for provisioning a new tenant organization."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = Field(default=None, max_length=64, description="Canonical tenant identifier")
    tenant_id: str | None = Field(
        default=None, max_length=64, description="Alias tenant identifier"
    )
    name: str = Field(..., max_length=200, description="Organization display name")
    balance_usd: str = Field(default="1000.00", description="Initial allocated budget balance")
    tier: str = Field(default="STANDARD", description="Tier (FREE, STANDARD, PRO, ENTERPRISE)")
    max_tokens_per_request: int = Field(default=4096, description="Token limit per request")
    monthly_budget_usd: str = Field(default="500.00", description="Monthly spending limit")
    max_requests_per_minute: int = Field(
        default=60, description="Rate limit in requests per minute"
    )
    contact_email: str | None = Field(default=None, description="Contact/ops email address")
    allowed_models: list[str] = Field(
        default_factory=lambda: [
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet",
            "gemini-1.5-flash",
        ],
        description="Allowed models for this tenant",
    )

    @property
    def resolved_id(self) -> str:
        """Resolve either 'id' or 'tenant_id' as canonical slug identifier."""
        slug = self.id or self.tenant_id
        if not slug or not slug.strip():
            raise ValueError("El identificador del tenant ('id' o 'tenant_id') es obligatorio.")
        return slug.strip()


class TenantBudgetResponse(BaseModel):
    """Schema representing tenant current budget figures with dual identifiers."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Canonical tenant identifier")
    tenant_id: str = Field(..., description="Alias tenant identifier")
    balance: str = Field(..., description="Current budget balance")
    reserved_amount: str = Field(..., description="Active reserved amount")
    available_balance: str = Field(..., description="Net available balance")
    currency: str = Field(..., description="Currency denomination")


class UpdateTenantPolicyRequest(BaseModel):
    """Schema for updating tenant operational governance policy."""

    model_config = ConfigDict(extra="forbid")

    tier: str | None = Field(default=None, description="Service tier")
    max_tokens_per_request: int | None = Field(default=None, description="Max tokens per request")
    monthly_budget_usd: str | None = Field(default=None, description="Monthly spending budget")
    max_requests_per_minute: int | None = Field(default=None, description="Max requests per minute")
    allowed_models: list[str] | None = Field(default=None, description="Allowed model IDs")


class TenantPolicyResponse(BaseModel):
    """Schema returned after policy update."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Canonical tenant identifier")
    tenant_id: str = Field(..., description="Alias tenant identifier")
    tier: str = Field(..., description="Service tier")
    max_tokens_per_request: int = Field(..., description="Token limit per request")
    monthly_budget_usd: str = Field(..., description="Monthly spending limit in USD")
    max_requests_per_minute: int = Field(default=60, description="RPM limit")
    allowed_models: list[str] = Field(..., description="Allowed model IDs")


class ReserveQuotaRequest(BaseModel):
    """Schema for testing or invoking quota reservation directly."""

    model_config = ConfigDict(frozen=True)

    estimated_cost: str = Field(..., description="Estimated cost in USD")
    model_id: str = Field(..., description="Target model ID to validate")


class ReserveQuotaResponse(BaseModel):
    """Schema returned on successful quota reservation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Canonical tenant identifier")
    tenant_id: str = Field(..., description="Alias tenant identifier")
    reserved_cost: str = Field(..., description="Reserved cost in USD")
    remaining_balance: str = Field(..., description="Remaining available balance")


__all__ = [
    "CreateTenantRequest",
    "ReserveQuotaRequest",
    "ReserveQuotaResponse",
    "TenantBudgetResponse",
    "TenantFinancialsSchema",
    "TenantLimitsSchema",
    "TenantMetadataSchema",
    "TenantPolicyResponse",
    "TenantSummaryResponse",
    "UpdateTenantPolicyRequest",
]
