# .agent/templates/unit-of-work/python/unit_of_work_port.template.py
"""
Template canónico para el Puerto Unit of Work en Python.
Reglas:
- Pertenece a src/application/shared/ports/.
- Expone un Context Manager asíncrono (__aenter__ / __aexit__).
- Métodos explícitos commit() y rollback().
"""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Type


class UnitOfWorkPort(ABC):
    async def __aenter__(self) -> "UnitOfWorkPort":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Confirma los cambios atómicamente y despacha eventos acumulados."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """Descarta transacciones pendientes en caso de fallo."""
        raise NotImplementedError
