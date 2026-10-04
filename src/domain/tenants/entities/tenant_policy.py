"""TenantPolicy entity and TenantTier enumeration."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TenantTier(StrEnum):
    """Service level tier for tenants."""

    FREE = "FREE"
    STANDARD = "STANDARD"
    ENTERPRISE = "ENTERPRISE"


@dataclass(frozen=True)
class TenantPolicy:
    """Contractual usage, quota, and model access policy for a tenant.

    Attributes:
        tier: Operational tier granting default rate limits and priority.
        max_tokens_per_request: Maximum prompt + completion tokens allowed.
        monthly_budget_usd: Spending ceiling in USD allocated per calendar month.
        allowed_models: Set of LLM model identifiers permitted for inference.
    """

    tier: TenantTier = TenantTier.FREE
    max_tokens_per_request: int = 4096
    monthly_budget_usd: Decimal = Decimal("50.00")
    allowed_models: frozenset[str] = frozenset({"gpt-4o-mini", "gemini-1.5-flash"})


__all__ = ["TenantPolicy", "TenantTier"]
