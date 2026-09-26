"""Template canónico para Pruebas Unitarias de Puertos de Repositorio (Driven Port).

Reglas:
- Verifica que el puerto abstracto no pueda instanciarse directamente (ABC).
- Verifica que una subclase concreta satisfaga el contrato esperado.
"""

from typing import List, Optional
from uuid import UUID, uuid4
import pytest

from src.domain.example.example_entity import ExampleEntity
from .repository_port.tt import ExampleRepositoryPort  # type: ignore[import-not-found]


def test_cannot_instantiate_abstract_repository_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        ExampleRepositoryPort()  # type: ignore[abstract]


def test_concrete_repository_port_implementation() -> None:
    class InMemoryExampleRepository(ExampleRepositoryPort):
        def __init__(self) -> None:
            self._storage: dict[UUID, ExampleEntity] = {}

        async def save(self, entity: ExampleEntity) -> None:
            self._storage[entity.id] = entity

        async def get_by_id(self, entity_id: UUID) -> Optional[ExampleEntity]:
            return self._storage.get(entity_id)

        async def list_all(self, limit: int = 50, offset: int = 0) -> List[ExampleEntity]:
            items = list(self._storage.values())
            return items[offset : offset + limit]

        async def delete(self, entity_id: UUID) -> None:
            self._storage.pop(entity_id, None)

    repo = InMemoryExampleRepository()
    entity = ExampleEntity(id=uuid4(), name="Test Entity")

    import asyncio

    asyncio.run(repo.save(entity))
    retrieved = asyncio.run(repo.get_by_id(entity.id))

    assert retrieved is not None
    assert retrieved.name == "Test Entity"
