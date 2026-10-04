"""Unit tests for main composition root and dynamic persistence wiring."""

from fastapi import FastAPI

from src.infrastructure.persistence.in_memory.unit_of_work import (
    InMemoryUnitOfWorkAdapter,
)
from src.infrastructure.shared.config.settings import PersistenceDriver, Settings
from src.main import create_app


def test_create_app_default_wires_in_memory() -> None:
    app = create_app(settings=Settings(PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY))
    assert isinstance(app, FastAPI)


def test_create_app_with_mssql_driver_wires_mssql_uow() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.MSSQL,
        DATABASE_URL="sqlite:///:memory:",
    )
    app = create_app(settings=settings)
    assert isinstance(app, FastAPI)


def test_create_app_with_explicit_uow() -> None:
    custom_uow = InMemoryUnitOfWorkAdapter()
    app = create_app(unit_of_work=custom_uow)
    assert isinstance(app, FastAPI)
