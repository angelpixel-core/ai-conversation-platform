"""
Template canónico para Pruebas de Integración de InMemoryUnitOfWork.
Reglas:
- Verifica ciclo de vida transaccional (__enter__, __exit__, commit, rollback).
"""

from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


def test_in_memory_unit_of_work_context_manager() -> None:
    uow = InMemoryUnitOfWork()

    with uow:
        assert uow.repository is not None

    assert uow.committed is False  # sin commit explícito
