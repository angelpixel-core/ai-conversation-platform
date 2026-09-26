# .agent/templates/unit-of-work/python/in_memory_unit_of_work_adapter.template.py
"""
Template canónico para el Adaptador en Memoria de Unit of Work en Python.
Reglas:
- Pertenece a src/infrastructure/persistence/in_memory/.
- Simula atomicidad en memoria sin dependencias de base de datos.
"""

from src.application.shared.ports.unit_of_work_port import UnitOfWorkPort


class InMemoryUnitOfWorkAdapter(UnitOfWorkPort):
    def __init__(self) -> None:
        self.committed: bool = False
        self.rolled_back: bool = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
