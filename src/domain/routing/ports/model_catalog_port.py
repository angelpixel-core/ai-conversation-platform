"""Driven port contract for LLM model catalog and routing specs."""

from abc import ABC, abstractmethod

from src.domain.routing.value_objects.model_route import ModelRoute


class ModelCatalogPort(ABC):
    """Abstract driven port for querying model routes and pricing."""

    @abstractmethod
    def get_route(self, model_id: str) -> ModelRoute | None:
        """Retrieves routing configuration for a given model ID."""
        raise NotImplementedError

    @abstractmethod
    def list_routes(self) -> list[ModelRoute]:
        """Lists all configured model routes."""
        raise NotImplementedError
