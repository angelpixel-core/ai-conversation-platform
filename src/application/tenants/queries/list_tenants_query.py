"""List tenants query and handler projecting unified tenant summaries."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.application.shared.ports.unit_of_work import UnitOfWorkPort


@dataclass(frozen=True)
class TenantFinancialsDTO:
    """Financial budget figures for a tenant."""

    currency: str
    balance: Decimal
    reserved_amount: Decimal
    available_balance: Decimal
    monthly_budget_usd: Decimal


@dataclass(frozen=True)
class TenantLimitsDTO:
    """Operational rate and token limits for a tenant."""

    max_tokens_per_request: int
    max_requests_per_minute: int


@dataclass(frozen=True)
class TenantMetadataDTO:
    """Audit and administrative metadata for a tenant."""

    created_at: datetime
    updated_at: datetime
    contact_email: str | None = None


@dataclass(frozen=True)
class TenantSummaryDTO:
    """Summary DTO representing tenant information in list views.

    Provides both flattened root attributes for backwards compatibility
    and enriched structured DTOs matching RFC-32 specifications.
    """

    id: str
    tenant_id: str
    name: str
    status: str
    tier: str
    balance: Decimal
    reserved_amount: Decimal
    available_balance: Decimal
    currency: str
    financials: TenantFinancialsDTO
    limits: TenantLimitsDTO
    metadata: TenantMetadataDTO


@dataclass(frozen=True)
class ListTenantsQuery:
    """Query DTO requesting list of all registered tenants."""

    status: str | None = None


class ListTenantsQueryHandler:
    """Application use case for reading and projecting tenant summaries."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        """Initialize the handler with a transactional UnitOfWork boundary.

        Args:
            unit_of_work: Transactional boundary port managing repository state.
        """
        self._unit_of_work = unit_of_work

    def handle(self, query: ListTenantsQuery | None = None) -> list[TenantSummaryDTO]:
        """Execute read query listing registered tenants.

        Args:
            query: Optional query filters.

        Returns:
            List of TenantSummaryDTO objects with dual ID and enriched structures.
        """
        with self._unit_of_work as uow:
            tenants = uow.tenants.list()
            results: list[TenantSummaryDTO] = []
            for t in tenants:
                if query and query.status and t.status.value != query.status:
                    continue

                financials = TenantFinancialsDTO(
                    currency=t.budget.currency,
                    balance=t.budget.balance,
                    reserved_amount=t.budget.reserved_amount,
                    available_balance=t.budget.available_balance,
                    monthly_budget_usd=t.policy.monthly_budget_usd,
                )
                limits = TenantLimitsDTO(
                    max_tokens_per_request=t.policy.max_tokens_per_request,
                    max_requests_per_minute=t.policy.max_requests_per_minute,
                )
                metadata = TenantMetadataDTO(
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                    contact_email=t.contact_email,
                )
                results.append(
                    TenantSummaryDTO(
                        id=str(t.id),
                        tenant_id=str(t.id),
                        name=t.name,
                        status=t.status.value,
                        tier=t.policy.tier.value,
                        balance=t.budget.balance,
                        reserved_amount=t.budget.reserved_amount,
                        available_balance=t.budget.available_balance,
                        currency=t.budget.currency,
                        financials=financials,
                        limits=limits,
                        metadata=metadata,
                    )
                )
            return results


__all__ = [
    "ListTenantsQuery",
    "ListTenantsQueryHandler",
    "TenantFinancialsDTO",
    "TenantLimitsDTO",
    "TenantMetadataDTO",
    "TenantSummaryDTO",
]
