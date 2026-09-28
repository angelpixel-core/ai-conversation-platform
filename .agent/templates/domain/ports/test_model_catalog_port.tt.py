"""Test template canónico para ModelCatalogPort."""

from decimal import Decimal
from typing import List, Optional
from ..value_objects.model_route import ModelRoute
from .model_catalog_port import ModelCatalogPort


class FakeModelCatalog(ModelCatalogPort):
    def __init__(self) -> None:
        self.routes: dict[str, ModelRoute] = {}

    def get_route(self, model_id: str) -> Optional[ModelRoute]:
        return self.routes.get(model_id)

    def list_routes(self) -> List[ModelRoute]:
        return list(self.routes.values())


def test_model_catalog_contract() -> None:
    catalog = FakeModelCatalog()
    route = ModelRoute(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_tokens=Decimal("0.00015"),
        cost_per_1k_output_tokens=Decimal("0.00060"),
    )
    catalog.routes["gpt-4o-mini"] = route

    assert catalog.get_route("gpt-4o-mini") == route
    assert catalog.get_route("non-existent") is None
    assert len(catalog.list_routes()) == 1
