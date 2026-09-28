"""TenantPolicy entity and TenantTier enumeration."""

from collections.abc import Set
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
    """Contractual usage, quota, and model access policy for a tenant."""

    tier: TenantTier = TenantTier.FREE
    max_tokens_per_request: int = 4096
    monthly_budget_usd: Decimal = Decimal("50.00")
    allowed_models: Set[str] = frozenset({"gpt-4o-mini", "gemini-1.5-flash"})
