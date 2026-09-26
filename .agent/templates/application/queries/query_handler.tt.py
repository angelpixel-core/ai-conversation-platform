# .agent/templates/query-handlers/python/query_handler.template.py
"""
Template canónico para un Query Handler en Python.
Reglas:
- Pertenece a la capa de Aplicación.
- Recibe repositorios de lectura o puertos de persistencia.
- No muta estado ni inicia transacciones de escritura.
- Devuelve DTOs de lectura (Read Models).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.application.example.queries.get_example_by_id_query import GetExampleByIdQuery
from src.domain.example.example_repository_port import ExampleRepositoryPort


@dataclass(frozen=True)
class ExampleReadModel:
    id: UUID
    name: str
    created_at: datetime


class GetExampleByIdQueryHandler:
    def __init__(self, repository: ExampleRepositoryPort) -> None:
        self._repository = repository

    async def handle(self, query: GetExampleByIdQuery) -> Optional[ExampleReadModel]:
        entity = await self._repository.get_by_id(query.entity_id)
        if not entity:
            return None

        return ExampleReadModel(
            id=entity.id,
            name=entity.name,
            created_at=entity.created_at,
        )
