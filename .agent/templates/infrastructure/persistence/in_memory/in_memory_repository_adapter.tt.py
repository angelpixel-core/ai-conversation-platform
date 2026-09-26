"""
Template canónico para un Adaptador de Repositorio en Memoria en Python.
Reglas:
- Pertenece a src/infrastructure/persistence/in_memory/.
- Implementa ExampleRepositoryPort (Driven Port).
- Utiliza estructuras concurrentes o diccionarios nativos.
- Mantiene copias independientes para evitar mutaciones externas inadvertidas.
"""

from typing import Dict, List, Optional
from uuid import UUID

from src.domain.example.example_entity import ExampleEntity
from src.domain.example.example_repository_port import ExampleRepositoryPort


class InMemoryExampleRepositoryAdapter(ExampleRepositoryPort):
    def __init__(self) -> None:
        self._storage: Dict[UUID, ExampleEntity] = {}

    async def save(self, entity: ExampleEntity) -> None:
        self._storage[entity.id] = entity

    async def get_by_id(self, entity_id: UUID) -> Optional[ExampleEntity]:
        return self._storage.get(entity_id)

    async def list_all(self, limit: int = 50, offset: int = 0) -> List[ExampleEntity]:
        items = list(self._storage.values())
        return items[offset : offset + limit]

    async def delete(self, entity_id: UUID) -> None:
        self._storage.pop(entity_id, None)

    def clear(self) -> None:
        """Helper para limpieza rápida entre suites de test."""
        self._storage.clear()
