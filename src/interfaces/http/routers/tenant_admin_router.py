"""Tenant and Policy administration HTTP router."""

from decimal import Decimal
from typing import NoReturn

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.tenants.commands.provision_tenant_command import (
    ProvisionTenantCommand,
    ProvisionTenantCommandHandler,
)
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommand,
    ReserveQuotaCommandHandler,
)
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.value_objects.tenant_id import TenantId


class TenantBudgetResponse(BaseModel):
    """Schema representing tenant current budget figures."""

    tenant_id: str
    balance: str
    reserved_amount: str
    available_balance: str
    currency: str


class CreateTenantRequest(BaseModel):
    """Schema for provisioning a new tenant."""

    id: str = Field(..., max_length=64, description="Unique tenant slug or identifier")
    name: str = Field(..., max_length=200, description="Organization display name")
    balance_usd: str = Field(default="1000.00", description="Initial allocated budget balance")
    tier: str = Field(default="STANDARD", description="Tier (FREE, STANDARD, ENTERPRISE)")
    max_tokens_per_request: int = Field(default=4096, description="Token limit per request")
    monthly_budget_usd: str = Field(default="500.00", description="Monthly spending limit")
    allowed_models: list[str] = Field(
        default_factory=lambda: [
            "gpt-4o",
            "gpt-4o-mini",
            "claude-3-5-sonnet",
            "gemini-1.5-flash",
        ],
        description="Allowed models for this tenant",
    )


class TenantSummaryResponse(BaseModel):
    """Schema for summarizing a tenant in list view."""

    tenant_id: str
    name: str
    status: str
    tier: str
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


def _handle_reserve_quota_error(id: str, exc: ValueError) -> NoReturn:
    msg = str(exc)
    msg_lower = msg.lower()
    if any(keyword in msg_lower for keyword in ("cuota excedida", "presupuesto", "saldo")):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Presupuesto insuficiente o cuota excedida para el tenant '{id}'. {msg}",
        ) from exc
    if "no encontrado" in msg_lower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=msg,
    ) from exc


def _build_updated_policy(
    current_policy: TenantPolicy, request: UpdateTenantPolicyRequest
) -> TenantPolicy:
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
    return TenantPolicy(
        tier=tier,
        max_tokens_per_request=max_tokens,
        monthly_budget_usd=monthly_budget,
        allowed_models=allowed_models,
    )


def _handle_create_tenant_error(exc: ValueError) -> NoReturn:
    msg = str(exc)
    if "ya existe" in msg.lower():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=msg,
    ) from exc


def _get_tenant_or_404(
    unit_of_work: UnitOfWorkPort, tenant_id: str, for_update: bool = False
) -> Tenant:
    tenant = (
        unit_of_work.tenants.get_for_update(TenantId(tenant_id))
        if for_update
        else unit_of_work.tenants.get(TenantId(tenant_id))
    )
    if tenant is None and tenant_id in ("corp-acme", "default-tenant"):
        demo_tenant = Tenant.create_demo(tenant_id)
        unit_of_work.tenants.add(demo_tenant)
        unit_of_work.commit()
        return demo_tenant
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' no encontrado.",
        )
    return tenant


def create_tenant_admin_router(unit_of_work: UnitOfWorkPort) -> APIRouter:
    """Factory creating the administration APIRouter for tenants."""
    router = APIRouter(prefix="/admin/tenants", tags=["Tenant Administration"])

    @router.post(
        "",
        response_model=TenantBudgetResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Provision a new tenant organization",
        description=(
            "Provisions a new tenant with initial allocated token budget, tier, "
            "model access control, and policy limits."
        ),
    )
    def create_tenant(request: CreateTenantRequest) -> TenantBudgetResponse:
        handler = ProvisionTenantCommandHandler(unit_of_work=unit_of_work)
        try:
            result = handler.handle(
                ProvisionTenantCommand(
                    tenant_id=request.id,
                    name=request.name,
                    initial_balance=Decimal(request.balance_usd),
                    tier=request.tier,
                    max_tokens_per_request=request.max_tokens_per_request,
                    monthly_budget_usd=Decimal(request.monthly_budget_usd),
                    allowed_models=frozenset(request.allowed_models),
                )
            )
        except ValueError as exc:
            _handle_create_tenant_error(exc)

        return TenantBudgetResponse(
            tenant_id=result.tenant_id,
            balance=f"{result.balance:.4f}",
            reserved_amount=f"{result.reserved_amount:.4f}",
            available_balance=f"{result.available_balance:.4f}",
            currency=result.currency,
        )

    @router.get(
        "",
        response_model=list[TenantSummaryResponse],
        summary="List all registered tenants",
        description=(
            "Lists all registered tenants with their status, tier, and current budget balance."
        ),
    )
    def list_tenants() -> list[TenantSummaryResponse]:
        with unit_of_work as uow:
            return [
                TenantSummaryResponse(
                    tenant_id=str(t.id),
                    name=t.name,
                    status=t.status.value,
                    tier=t.policy.tier.value,
                    balance=f"{t.budget.balance:.4f}",
                    reserved_amount=f"{t.budget.reserved_amount:.4f}",
                    available_balance=f"{t.budget.available_balance:.4f}",
                    currency=t.budget.currency,
                )
                for t in uow.tenants.list()
            ]

    @router.get(
        "/{id}/budget",
        response_model=TenantBudgetResponse,
        summary="Get tenant budget status",
        description=(
            "Retrieves current token budget, reserved quota, and available balance for a tenant."
        ),
    )
    def get_tenant_budget(id: str) -> TenantBudgetResponse:
        with unit_of_work as uow:
            tenant = _get_tenant_or_404(uow, id)
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
        description=(
            "Updates governance policy for a tenant including tier, max tokens per request, "
            "and allowed models."
        ),
    )
    def update_tenant_policy(id: str, request: UpdateTenantPolicyRequest) -> TenantPolicyResponse:
        with unit_of_work as uow:
            tenant = _get_tenant_or_404(uow, id, for_update=True)
            updated_policy = _build_updated_policy(tenant.policy, request)
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
        description=(
            "Atomically reserves token quota for an upcoming inference or chat completion request."
        ),
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
            _handle_reserve_quota_error(id, exc)

        return ReserveQuotaResponse(
            tenant_id=id,
            reserved_cost=f"{result.reserved_amount:.4f}",
            remaining_balance=f"{result.remaining_balance:.4f}",
        )

    return router
