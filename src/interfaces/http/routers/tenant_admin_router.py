"""Tenant and Policy administration HTTP router."""

from decimal import Decimal
from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.tenants.commands.provision_tenant_command import (
    ProvisionTenantCommand,
    ProvisionTenantCommandHandler,
)
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommand,
    ReserveQuotaCommandHandler,
)
from src.application.tenants.commands.update_tenant_policy_command import (
    UpdateTenantPolicyCommand,
    UpdateTenantPolicyCommandHandler,
)
from src.application.tenants.queries.get_tenant_budget_query import (
    GetTenantBudgetQuery,
    GetTenantBudgetQueryHandler,
)
from src.application.tenants.queries.list_tenants_query import (
    ListTenantsQuery,
    ListTenantsQueryHandler,
)
from src.domain.tenants.exceptions import TenantAlreadyExistsError, TenantNotFoundError
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


def _handle_reserve_quota_error(tenant_id: str, exc: ValueError) -> NoReturn:
    msg = str(exc)
    msg_lower = msg.lower()
    if any(keyword in msg_lower for keyword in ("cuota excedida", "presupuesto", "saldo")):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Presupuesto insuficiente o cuota excedida para el tenant '{tenant_id}'. {msg}",
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


def _resolve_tenant_handlers(
    provision_handler: ProvisionTenantCommandHandler | None,
    list_handler: ListTenantsQueryHandler | None,
    get_budget_handler: GetTenantBudgetQueryHandler | None,
    update_policy_handler: UpdateTenantPolicyCommandHandler | None,
    reserve_quota_handler: ReserveQuotaCommandHandler | None,
    unit_of_work: UnitOfWorkPort | None,
) -> tuple[
    ProvisionTenantCommandHandler,
    ListTenantsQueryHandler,
    GetTenantBudgetQueryHandler,
    UpdateTenantPolicyCommandHandler,
    ReserveQuotaCommandHandler,
]:
    """Resolve and validate injected handlers or wire fallback via unit_of_work."""
    if unit_of_work is not None:
        provision_handler = provision_handler or ProvisionTenantCommandHandler(unit_of_work)
        list_handler = list_handler or ListTenantsQueryHandler(unit_of_work)
        get_budget_handler = get_budget_handler or GetTenantBudgetQueryHandler(unit_of_work)
        update_policy_handler = update_policy_handler or UpdateTenantPolicyCommandHandler(
            unit_of_work
        )
        reserve_quota_handler = reserve_quota_handler or ReserveQuotaCommandHandler(unit_of_work)

    if None in (
        provision_handler,
        list_handler,
        get_budget_handler,
        update_policy_handler,
        reserve_quota_handler,
    ):
        raise ValueError("All CQRS handlers or a UnitOfWorkPort must be provided to tenant router.")

    assert provision_handler is not None
    assert list_handler is not None
    assert get_budget_handler is not None
    assert update_policy_handler is not None
    assert reserve_quota_handler is not None

    return (
        provision_handler,
        list_handler,
        get_budget_handler,
        update_policy_handler,
        reserve_quota_handler,
    )


def _build_provision_command(request: CreateTenantRequest) -> ProvisionTenantCommand:
    """Build ProvisionTenantCommand from validated HTTP request."""
    return ProvisionTenantCommand(
        tenant_id=request.resolved_id,
        name=request.name,
        initial_balance=Decimal(request.balance_usd),
        tier=request.tier,
        max_tokens_per_request=request.max_tokens_per_request,
        monthly_budget_usd=Decimal(request.monthly_budget_usd),
        max_requests_per_minute=request.max_requests_per_minute,
        contact_email=request.contact_email,
        allowed_models=frozenset(request.allowed_models),
    )


def _build_update_policy_command(
    tenant_id: str, request: UpdateTenantPolicyRequest
) -> UpdateTenantPolicyCommand:
    """Build UpdateTenantPolicyCommand handling optional parameters."""
    monthly_budget = (
        Decimal(request.monthly_budget_usd) if request.monthly_budget_usd is not None else None
    )
    allowed_models = (
        frozenset(request.allowed_models) if request.allowed_models is not None else None
    )
    return UpdateTenantPolicyCommand(
        tenant_id=tenant_id,
        tier=request.tier,
        max_tokens_per_request=request.max_tokens_per_request,
        monthly_budget_usd=monthly_budget,
        max_requests_per_minute=request.max_requests_per_minute,
        allowed_models=allowed_models,
    )


def _register_command_routes(
    router: APIRouter,
    provision_handler: ProvisionTenantCommandHandler,
    update_policy_handler: UpdateTenantPolicyCommandHandler,
    reserve_quota_handler: ReserveQuotaCommandHandler,
) -> None:
    """Register CQRS command (write) endpoints on the admin router."""

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
        try:
            cmd = _build_provision_command(request)
            result = provision_handler.handle(cmd)
        except TenantAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        return TenantBudgetResponse(
            id=result.id,
            tenant_id=result.tenant_id,
            balance=f"{result.balance:.4f}",
            reserved_amount=f"{result.reserved_amount:.4f}",
            available_balance=f"{result.available_balance:.4f}",
            currency=result.currency,
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
        try:
            cmd = _build_update_policy_command(id, request)
            result = update_policy_handler.handle(cmd)
        except TenantNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        return TenantPolicyResponse(
            id=result.id,
            tenant_id=result.tenant_id,
            tier=result.tier,
            max_tokens_per_request=result.max_tokens_per_request,
            monthly_budget_usd=f"{result.monthly_budget_usd:.4f}",
            max_requests_per_minute=result.max_requests_per_minute,
            allowed_models=result.allowed_models,
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
        try:
            result = reserve_quota_handler.handle(
                ReserveQuotaCommand(
                    tenant_id=id,
                    estimated_cost=Decimal(request.estimated_cost),
                    model_id=request.model_id,
                )
            )
        except ValueError as exc:
            _handle_reserve_quota_error(id, exc)

        return ReserveQuotaResponse(
            id=id,
            tenant_id=id,
            reserved_cost=f"{result.reserved_amount:.4f}",
            remaining_balance=f"{result.remaining_balance:.4f}",
        )


def _register_query_routes(
    router: APIRouter,
    list_handler: ListTenantsQueryHandler,
    get_budget_handler: GetTenantBudgetQueryHandler,
) -> None:
    """Register CQRS query (read) endpoints on the admin router."""

    @router.get(
        "",
        response_model=list[TenantSummaryResponse],
        summary="List all registered tenants",
        description=(
            "Lists all registered tenants with dual identifiers, status, tier, "
            "and enriched RFC-32 financial, limits, and metadata breakdowns."
        ),
    )
    def list_tenants() -> list[TenantSummaryResponse]:
        results = list_handler.handle(ListTenantsQuery())
        return [
            TenantSummaryResponse(
                id=t.id,
                tenant_id=t.tenant_id,
                name=t.name,
                status=t.status,
                tier=t.tier,
                balance=f"{t.balance:.4f}",
                reserved_amount=f"{t.reserved_amount:.4f}",
                available_balance=f"{t.available_balance:.4f}",
                currency=t.currency,
                financials=TenantFinancialsSchema(
                    currency=t.financials.currency,
                    balance=f"{t.financials.balance:.4f}",
                    reserved_amount=f"{t.financials.reserved_amount:.4f}",
                    available_balance=f"{t.financials.available_balance:.4f}",
                    monthly_budget_usd=f"{t.financials.monthly_budget_usd:.4f}",
                ),
                limits=TenantLimitsSchema(
                    max_tokens_per_request=t.limits.max_tokens_per_request,
                    max_requests_per_minute=t.limits.max_requests_per_minute,
                ),
                metadata=TenantMetadataSchema(
                    created_at=t.metadata.created_at.isoformat(),
                    updated_at=t.metadata.updated_at.isoformat(),
                    contact_email=t.metadata.contact_email,
                ),
            )
            for t in results
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
        try:
            result = get_budget_handler.handle(GetTenantBudgetQuery(tenant_id=id))
        except TenantNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        return TenantBudgetResponse(
            id=result.id,
            tenant_id=result.tenant_id,
            balance=f"{result.balance:.4f}",
            reserved_amount=f"{result.reserved_amount:.4f}",
            available_balance=f"{result.available_balance:.4f}",
            currency=result.currency,
        )


def create_tenant_admin_router(
    provision_handler: ProvisionTenantCommandHandler | None = None,
    list_handler: ListTenantsQueryHandler | None = None,
    get_budget_handler: GetTenantBudgetQueryHandler | None = None,
    update_policy_handler: UpdateTenantPolicyCommandHandler | None = None,
    reserve_quota_handler: ReserveQuotaCommandHandler | None = None,
    unit_of_work: UnitOfWorkPort | None = None,
) -> APIRouter:
    """Factory creating the administration APIRouter for tenants.

    Accepts explicitly injected CQRS command/query handlers or wires them
    from unit_of_work if provided for backwards compatibility.
    """
    router = APIRouter(prefix="/admin/tenants", tags=["Tenant Administration"])

    (
        p_handler,
        l_handler,
        b_handler,
        u_handler,
        r_handler,
    ) = _resolve_tenant_handlers(
        provision_handler,
        list_handler,
        get_budget_handler,
        update_policy_handler,
        reserve_quota_handler,
        unit_of_work,
    )

    _register_command_routes(router, p_handler, u_handler, r_handler)
    _register_query_routes(router, l_handler, b_handler)

    return router


__all__ = ["create_tenant_admin_router"]
