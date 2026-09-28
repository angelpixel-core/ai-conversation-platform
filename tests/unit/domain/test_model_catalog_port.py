"""Unit tests for ModelCatalogPort contract."""

from decimal import Decimal

from src.domain.routing.ports.model_catalog_port import ModelCatalogPort

from src.domain.routing.value_objects.model_route import ModelRoute


class FakeModelCatalog(ModelCatalogPort):
    """In-memory implementation to test ModelCatalogPort contract."""

    def __init__(self) -> None:
        self.routes: dict[str, ModelRoute] = {}

    def get_route(self, model_id: str) -> ModelRoute | None:
        return self.routes.get(model_id)

    def list_routes(self) -> list[ModelRoute]:
        return list(self.routes.values())


def test_model_catalog_contract_get_route() -> None:
    catalog = FakeModelCatalog()
    route = ModelRoute(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_tokens=Decimal("0.00015"),
        cost_per_1k_output_tokens=Decimal("0.00060"),
        fallback_model_id="gemini-1.5-flash",
    )
    catalog.routes["gpt-4o-mini"] = route

    assert catalog.get_route("gpt-4o-mini") == route
    assert catalog.get_route("missing-model") is None


def test_model_catalog_contract_list_routes() -> None:
    catalog = FakeModelCatalog()
    route1 = ModelRoute(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_tokens=Decimal("0.00015"),
        cost_per_1k_output_tokens=Decimal("0.00060"),
    )
    route2 = ModelRoute(
        provider="google",
        model_name="gemini-1.5-flash",
        cost_per_1k_input_tokens=Decimal("0.00010"),
        cost_per_1k_output_tokens=Decimal("0.00040"),
    )
    catalog.routes["gpt-4o-mini"] = route1
    catalog.routes["gemini-1.5-flash"] = route2

    routes = catalog.list_routes()
    assert len(routes) == 2
