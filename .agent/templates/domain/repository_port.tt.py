"""
Template canónico para un Puerto de Repositorio (Driven Port) en Python.
Reglas:
- Pertenece a la capa de Dominio.
- Utiliza ABC (Abstract Base Class) y métodos asíncronos (@abstractmethod).
- Trabaja exclusivamente con identificadores nativos (UUID) y la Entidad del dominio.
- No contiene lógica ni dependencias a librerías de persistencia (SQLAlchemy, Redis, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.example.example_entity import ExampleEntity


class ExampleRepositoryPort(ABC):
    """Contrato abstracto para la persistencia del agregado ExampleEntity."""

    @abstractmethod
    async def save(self, entity: ExampleEntity) -> None:
        """Persiste o actualiza el estado de la entidad."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[ExampleEntity]:
        """Recupera una entidad por su ID único. Retorna None si no existe."""
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, limit: int = 50, offset: int = 0) -> List[ExampleEntity]:
        """Lista entidades con paginación básica."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None:
        """Elimina una entidad por su ID."""
        raise NotImplementedError
