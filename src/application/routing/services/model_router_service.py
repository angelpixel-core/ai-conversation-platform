"""Application service for dynamic LLM model routing and policy evaluation."""

from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.domain.routing.value_objects.model_route import ModelRoute
from src.domain.tenants.entities.tenant import Tenant


class ModelRouterService:
    """Selects optimal model routes based on tenant policies, token limits, and fallbacks."""

    def __init__(self, catalog: ModelCatalogPort) -> None:
        self._catalog = catalog

    def resolve_route(
        self,
        tenant: Tenant,
        requested_model: str | None = None,
        estimated_prompt_tokens: int = 256,
        is_fallback_attempt: bool = False,
        failed_model_id: str | None = None,
    ) -> ModelRoute:
        """Determines the appropriate model route evaluating tenant policy and catalog."""
        # 1. Fallback resolution if primary failed
        if is_fallback_attempt and failed_model_id:
            failed_route = self._catalog.get_route(failed_model_id)
            if failed_route and failed_route.fallback_model_id:
                fallback_route = self._catalog.get_route(failed_route.fallback_model_id)
                if fallback_route:
                    return fallback_route

        # 2. Preferred or default model selection
        target_model = requested_model or "gpt-4o-mini"
        if target_model not in tenant.policy.allowed_models:
            # Fallback to an allowed model from tenant policy
            target_model = next(iter(tenant.policy.allowed_models))

        route = self._catalog.get_route(target_model)
        if route is None:
            raise ValueError(
                f"No existe configuración en el catálogo para el modelo '{target_model}'."
            )

        # 3. Validate context window
        if estimated_prompt_tokens > route.max_context_tokens:
            raise ValueError(
                f"El volumen de tokens de entrada ({estimated_prompt_tokens}) "
                f"excede el límite del modelo ({route.max_context_tokens})."
            )

        return route
