"""In-memory model catalog adapter."""

from decimal import Decimal

from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.domain.routing.value_objects.model_route import ModelRoute

DEFAULT_MODEL_ROUTES: list[ModelRoute] = [
    ModelRoute(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_tokens=Decimal("0.00015"),
        cost_per_1k_output_tokens=Decimal("0.00060"),
        max_context_tokens=128000,
        tier_required="FREE",
    ),
    ModelRoute(
        provider="openai",
        model_name="gpt-4o",
        cost_per_1k_input_tokens=Decimal("0.00250"),
        cost_per_1k_output_tokens=Decimal("0.01000"),
        fallback_model_id="gpt-4o-mini",
        max_context_tokens=128000,
        tier_required="STANDARD",
    ),
    ModelRoute(
        provider="anthropic",
        model_name="claude-3-5-sonnet",
        cost_per_1k_input_tokens=Decimal("0.00300"),
        cost_per_1k_output_tokens=Decimal("0.01500"),
        fallback_model_id="gpt-4o",
        max_context_tokens=200000,
        tier_required="ENTERPRISE",
    ),
]


class InMemoryModelCatalogAdapter(ModelCatalogPort):
    """In-memory catalog of supported model routes and pricing specifications."""

    def __init__(self, routes: list[ModelRoute] | None = None) -> None:
        initial_routes = routes if routes is not None else DEFAULT_MODEL_ROUTES
        self._routes: dict[str, ModelRoute] = {r.model_name: r for r in initial_routes}

    def get_route(self, model_id: str) -> ModelRoute | None:
        return self._routes.get(model_id)

    def list_routes(self) -> list[ModelRoute]:
        return list(self._routes.values())

    def register_route(self, route: ModelRoute) -> None:
        self._routes[route.model_name] = route
