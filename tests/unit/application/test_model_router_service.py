"""Unit tests for ModelRouterService application service."""

from decimal import Decimal

import pytest
from src.application.routing.services.model_router_service import ModelRouterService

from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.domain.routing.value_objects.model_route import ModelRoute
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.entities.tenant_policy import TenantPolicy
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId


class FakeCatalog(ModelCatalogPort):
    def __init__(self) -> None:
        self.routes = {
            "gpt-4o-mini": ModelRoute(
                provider="openai",
                model_name="gpt-4o-mini",
                cost_per_1k_input_tokens=Decimal("0.00015"),
                cost_per_1k_output_tokens=Decimal("0.00060"),
                fallback_model_id="gemini-1.5-flash",
                max_context_tokens=8192,
            ),
            "gemini-1.5-flash": ModelRoute(
                provider="google",
                model_name="gemini-1.5-flash",
                cost_per_1k_input_tokens=Decimal("0.00010"),
                cost_per_1k_output_tokens=Decimal("0.00040"),
                max_context_tokens=16384,
            ),
        }

    def get_route(self, model_id: str) -> ModelRoute | None:
        return self.routes.get(model_id)

    def list_routes(self) -> list[ModelRoute]:
        return list(self.routes.values())


def test_model_router_resolves_allowed_model() -> None:
    catalog = FakeCatalog()
    service = ModelRouterService(catalog=catalog)
    tenant = Tenant(
        tenant_id=TenantId("tenant-1"),
        name="Tenant 1",
        budget=MonetaryBudget(balance=Decimal("100.00")),
        policy=TenantPolicy(allowed_models=frozenset({"gpt-4o-mini", "gemini-1.5-flash"})),
    )

    route = service.resolve_route(tenant, requested_model="gpt-4o-mini")
    assert route.model_name == "gpt-4o-mini"
    assert route.provider == "openai"


def test_model_router_resolves_fallback_when_primary_fails() -> None:
    catalog = FakeCatalog()
    service = ModelRouterService(catalog=catalog)
    tenant = Tenant(
        tenant_id=TenantId("tenant-1"),
        name="Tenant 1",
        budget=MonetaryBudget(balance=Decimal("100.00")),
    )

    route = service.resolve_route(
        tenant,
        is_fallback_attempt=True,
        failed_model_id="gpt-4o-mini",
    )
    assert route.model_name == "gemini-1.5-flash"
    assert route.provider == "google"


def test_model_router_context_tokens_exceeded_raises_error() -> None:
    catalog = FakeCatalog()
    service = ModelRouterService(catalog=catalog)
    tenant = Tenant(
        tenant_id=TenantId("tenant-1"),
        name="Tenant 1",
        budget=MonetaryBudget(balance=Decimal("100.00")),
    )

    with pytest.raises(ValueError, match="excede el límite del modelo"):
        service.resolve_route(tenant, requested_model="gpt-4o-mini", estimated_prompt_tokens=90000)


def test_model_router_unknown_model_raises_error() -> None:
    catalog = FakeCatalog()
    service = ModelRouterService(catalog=catalog)
    tenant = Tenant(
        tenant_id=TenantId("tenant-1"),
        name="Tenant 1",
        budget=MonetaryBudget(balance=Decimal("100.00")),
        policy=TenantPolicy(allowed_models=frozenset({"unknown-model-xyz"})),
    )

    with pytest.raises(ValueError, match="No existe configuración en el catálogo"):
        service.resolve_route(tenant, requested_model="unknown-model-xyz")
