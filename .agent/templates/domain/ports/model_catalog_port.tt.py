"""Template canónico para el Puerto de Catálogo de Modelos (ModelCatalogPort).

Reglas:
- Pertenece a la capa de Dominio (Driven Port).
- Expone contratos para consultar modelos LLM y sus costos configurados.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..value_objects.model_route import ModelRoute


class ModelCatalogPort(ABC):
    """Contrato abstracto para consultar las rutas y modelos disponibles."""

    @abstractmethod
    def get_route(self, model_id: str) -> Optional[ModelRoute]:
        """Obtiene la configuración de ruta y costo para un identificador de modelo."""
        raise NotImplementedError

    @abstractmethod
    def list_routes(self) -> List[ModelRoute]:
        """Lista todas las rutas de modelos disponibles en la plataforma."""
        raise NotImplementedError
