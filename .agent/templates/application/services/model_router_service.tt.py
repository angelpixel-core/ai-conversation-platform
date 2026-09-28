"""Template canónico para el Servicio de Aplicación ModelRouterService.

Reglas:
- Pertenece a la capa de Aplicación (src/application/routing/services/).
- Orquesta la selección dinámica de modelos según la política del inquilino y el catálogo.
- Resuelve rutas principales y rutas de contingencia (fallback).
"""

from decimal import Decimal
from typing import Optional

from src.domain.routing.ports.model_catalog_port import ModelCatalogPort
from src.domain.routing.value_objects.model_route import ModelRoute
from src.domain.tenants.entities.tenant_entity import Tenant


class ModelRouterService:
    """Servicio encargado de seleccionar dinámicamente la ruta óptima de modelo para un inquilino."""

    def __init__(self, catalog: ModelCatalogPort) -> None:
        self._catalog = catalog

    def resolve_route(
        self,
        tenant: Tenant,
        requested_model: Optional[str] = None,
        estimated_prompt_tokens: int = 256,
        is_fallback_attempt: bool = False,
        failed_model_id: Optional[str] = None,
    ) -> ModelRoute:
        """Determina la ruta de modelo adecuada evaluando la política del tenant y el catálogo."""
        # 1. Si es un intento de fallback por caída del primario:
        if is_fallback_attempt and failed_model_id:
            failed_route = self._catalog.get_route(failed_model_id)
            if failed_route and failed_route.fallback_model_id:
                fallback_route = self._catalog.get_route(failed_route.fallback_model_id)
                if fallback_route:
                    return fallback_route

        # 2. Selección de modelo preferido o por defecto
        target_model = requested_model or "gpt-4o-mini"
        if target_model not in tenant.policy.allowed_models:
            # Fallback a un modelo permitido del tenant
            target_model = next(iter(tenant.policy.allowed_models))

        route = self._catalog.get_route(target_model)
        if route is None:
            raise ValueError(f"No existe configuración en el catálogo para el modelo '{target_model}'.")

        # 3. Validar ventana de contexto
        if estimated_prompt_tokens > route.max_context_tokens:
            raise ValueError(
                f"El volumen de tokens de entrada ({estimated_prompt_tokens}) excede el límite del modelo ({route.max_context_tokens})."
            )

        return route
