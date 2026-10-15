"""TenantPolicy entity and TenantTier enumeration."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TenantTier(StrEnum):
    """Service level tier for tenants."""

    FREE = "FREE"
    STANDARD = "STANDARD"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


@dataclass(frozen=True)
class TenantPolicy:
    """Contractual usage, quota, and model access policy for a tenant.

    Attributes:
        tier: Operational tier granting default rate limits and priority.
        max_tokens_per_request: Maximum prompt + completion tokens allowed.
        monthly_budget_usd: Spending ceiling in USD allocated per calendar month.
        allowed_models: Set of LLM model identifiers permitted for inference.
        max_requests_per_minute: Maximum API invocations allowed per minute.
    """

    tier: TenantTier = TenantTier.FREE
    max_tokens_per_request: int = 4096
    monthly_budget_usd: Decimal = Decimal("50.00")
    allowed_models: frozenset[str] = frozenset({"gpt-4o-mini", "gemini-1.5-flash"})
    max_requests_per_minute: int = 60

    @classmethod
    def default_for_tier(cls, tier: TenantTier | str) -> "TenantPolicy":
        """Factory creating canonical default policy according to TenantTier SLA."""
        resolved_tier = TenantTier(tier) if isinstance(tier, str) else tier
        match resolved_tier:
            case TenantTier.FREE:
                return cls(
                    tier=TenantTier.FREE,
                    max_tokens_per_request=2048,
                    monthly_budget_usd=Decimal("50.00"),
                    allowed_models=frozenset({"gpt-4o-mini", "gemini-1.5-flash"}),
                    max_requests_per_minute=30,
                )
            case TenantTier.STANDARD:
                return cls(
                    tier=TenantTier.STANDARD,
                    max_tokens_per_request=4096,
                    monthly_budget_usd=Decimal("500.00"),
                    allowed_models=frozenset(
                        {"gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-flash"}
                    ),
                    max_requests_per_minute=60,
                )
            case TenantTier.PRO:
                return cls(
                    tier=TenantTier.PRO,
                    max_tokens_per_request=8192,
                    monthly_budget_usd=Decimal("2000.00"),
                    allowed_models=frozenset(
                        {
                            "gpt-4o",
                            "gpt-4o-mini",
                            "claude-3-5-sonnet",
                            "gemini-1.5-flash",
                            "o1-mini",
                        }
                    ),
                    max_requests_per_minute=120,
                )
            case TenantTier.ENTERPRISE:
                return cls(
                    tier=TenantTier.ENTERPRISE,
                    max_tokens_per_request=16384,
                    monthly_budget_usd=Decimal("10000.00"),
                    allowed_models=frozenset(
                        {
                            "gpt-4o",
                            "gpt-4o-mini",
                            "claude-3-5-sonnet",
                            "gemini-1.5-flash",
                            "o1",
                            "o1-mini",
                            "claude-3-opus",
                        }
                    ),
                    max_requests_per_minute=300,
                )


__all__ = ["TenantPolicy", "TenantTier"]
