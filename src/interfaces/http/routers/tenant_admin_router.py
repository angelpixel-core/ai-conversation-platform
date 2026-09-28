"""Tenant and Policy administration HTTP router."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.application.shared.ports.unit_of_work import UnitOfWork
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommand,
    ReserveQuotaCommandHandler,
)
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.tenant_id import TenantId


class TenantBudgetResponse(BaseModel):
    """Schema representing tenant current budget figures."""

    tenant_id: str
    balance: str
    reserved_amount: str
    available_balance: str
    currency: str


class UpdateTenantPolicyRequest(BaseModel):
    """Schema for updating tenant operational governance policy."""

    tier: str | None = None
    max_tokens_per_request: int | None = None
    monthly_budget_usd: str | None = None
    allowed_models: list[str] | None = None


class TenantPolicyResponse(BaseModel):
    """Schema returned after policy update."""

    tenant_id: str
    tier: str
    max_tokens_per_request: int
    monthly_budget_usd: str
    allowed_models: list[str]


class ReserveQuotaRequest(BaseModel):
    """Schema for testing or invoking quota reservation directly."""

    estimated_cost: str = Field(..., description="Estimated cost in USD")
    model_id: str = Field(..., description="Target model ID to validate")


class ReserveQuotaResponse(BaseModel):
    """Schema returned on successful quota reservation."""

    tenant_id: str
    reserved_cost: str
    remaining_balance: str


def create_tenant_admin_router(unit_of_work: UnitOfWork) -> APIRouter:
    """Factory creating the administration APIRouter for tenants."""
    router = APIRouter(prefix="/admin/tenants", tags=["Tenant Administration"])

    @router.get(
        "/{id}/budget",
        response_model=TenantBudgetResponse,
        summary="Get tenant budget status",
    )
    def get_tenant_budget(id: str) -> TenantBudgetResponse:
        with unit_of_work as uow:
            tenant = uow.tenants.get(TenantId(id))
            if tenant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{id}' no encontrado.",
                )
            return TenantBudgetResponse(
                tenant_id=id,
                balance=f"{tenant.budget.balance:.4f}",
                reserved_amount=f"{tenant.budget.reserved_amount:.4f}",
                available_balance=f"{tenant.budget.available_balance:.4f}",
                currency=tenant.budget.currency,
            )

    @router.patch(
        "/{id}/policy",
        response_model=TenantPolicyResponse,
        summary="Update tenant governance policy",
    )
    def update_tenant_policy(id: str, request: UpdateTenantPolicyRequest) -> TenantPolicyResponse:
        with unit_of_work as uow:
            tenant = uow.tenants.get_for_update(TenantId(id))
            if tenant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{id}' no encontrado.",
                )

            current_policy = tenant.policy
            tier = TenantTier(request.tier) if request.tier else current_policy.tier
            max_tokens = (
                request.max_tokens_per_request
                if request.max_tokens_per_request is not None
                else current_policy.max_tokens_per_request
            )
            monthly_budget = (
                Decimal(request.monthly_budget_usd)
                if request.monthly_budget_usd is not None
                else current_policy.monthly_budget_usd
            )
            allowed_models = (
                frozenset(request.allowed_models)
                if request.allowed_models is not None
                else current_policy.allowed_models
            )

            updated_policy = TenantPolicy(
                tier=tier,
                max_tokens_per_request=max_tokens,
                monthly_budget_usd=monthly_budget,
                allowed_models=allowed_models,
            )

            # Reconstitute tenant with updated policy
            tenant._policy = updated_policy  # pyright: ignore[reportPrivateUsage]
            uow.tenants.add(tenant)
            uow.commit()

            return TenantPolicyResponse(
                tenant_id=id,
                tier=updated_policy.tier.value,
                max_tokens_per_request=updated_policy.max_tokens_per_request,
                monthly_budget_usd=f"{updated_policy.monthly_budget_usd:.4f}",
                allowed_models=sorted(updated_policy.allowed_models),
            )

    @router.post(
        "/{id}/reserve",
        response_model=ReserveQuotaResponse,
        summary="Reserve inference quota for tenant",
    )
    def reserve_quota(id: str, request: ReserveQuotaRequest) -> ReserveQuotaResponse:
        handler = ReserveQuotaCommandHandler(unit_of_work=unit_of_work)
        try:
            result = handler.handle(
                ReserveQuotaCommand(
                    tenant_id=id,
                    estimated_cost=Decimal(request.estimated_cost),
                    model_id=request.model_id,
                )
            )
        except ValueError as exc:
            msg = str(exc)
            if (
                "cuota excedida" in msg.lower()
                or "presupuesto" in msg.lower()
                or "saldo" in msg.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        f"Presupuesto insuficiente o cuota excedida para el tenant '{id}'. {msg}"
                    ),
                ) from exc
            if "no encontrado" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=msg,
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            ) from exc

        return ReserveQuotaResponse(
            tenant_id=id,
            reserved_cost=f"{result.reserved_amount:.4f}",
            remaining_balance=f"{result.remaining_balance:.4f}",
        )

    return router
