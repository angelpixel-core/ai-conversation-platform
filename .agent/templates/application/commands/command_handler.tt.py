# .agent/templates/command-handlers/python/command_handler.template.py
"""
Template canónico para un Command Handler en Python.
Reglas:
- Pertenece a la capa de Aplicación.
- Recibe dependencias abstractas (Ports) inyectadas en el constructor.
- Coordina la creación/mutación de la entidad y la persistencia atómica.
"""

from dataclasses import dataclass
from uuid import UUID

from src.application.example.commands.create_example_command import CreateExampleCommand
from src.application.shared.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.example.example_entity import ExampleEntity
from src.domain.example.example_repository_port import ExampleRepositoryPort


@dataclass(frozen=True)
class CreateExampleResult:
    entity_id: UUID


class CreateExampleCommandHandler:
    def __init__(
        self,
        repository: ExampleRepositoryPort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._repository = repository
        self._uow = unit_of_work

    async def handle(self, command: CreateExampleCommand) -> CreateExampleResult:
        # 1. Ejecutar regla de negocio en el Dominio (Factory method)
        entity = ExampleEntity.create(
            name=command.name,
            entity_id=command.custom_id,
        )

        # 2. Persistir atómicamente a través de la Unidad de Trabajo
        async with self._uow:
            await self._repository.save(entity)
            await self._uow.commit()

        return CreateExampleResult(entity_id=entity.id)
