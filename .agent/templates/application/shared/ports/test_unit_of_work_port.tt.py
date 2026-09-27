"""Template canónico para Pruebas Unitarias del Puerto Unit of Work (Application Port).

Reglas:
- Verifica que el puerto abstracto no pueda instanciarse directamente (ABC).
- Verifica que el context manager asíncrono invoque rollback automáticamente ante excepciones.
- Usa @pytest.mark.anyio.
"""

from types import TracebackType
from typing import Optional, Type
import pytest

from .unit_of_work_port.tt import UnitOfWorkPort  # type: ignore[import-not-found]


def test_cannot_instantiate_abstract_uow_port() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        UnitOfWorkPort()  # type: ignore[abstract]


@pytest.mark.anyio
async def test_concrete_uow_rollback_on_exception() -> None:
    class FakeUnitOfWork(UnitOfWorkPort):
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    uow = FakeUnitOfWork()

    with pytest.raises(ValueError, match="Boom"):
        async with uow:
            raise ValueError("Boom")

    assert uow.rolled_back is True
    assert uow.committed is False


@pytest.mark.anyio
async def test_concrete_uow_commit_flow() -> None:
    class FakeUnitOfWork(UnitOfWorkPort):
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    uow = FakeUnitOfWork()

    async with uow:
        await uow.commit()

    assert uow.committed is True
    assert uow.rolled_back is False
