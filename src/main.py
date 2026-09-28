"""Application entrypoint.

The composition root lives in src/container.py so infrastructure choices are explicit and
easy to replace when moving between local in-memory adapters and MSSQL/PostgreSQL/cloud.
"""

from fastapi import FastAPI

from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.container import create_app_container
from src.infrastructure.shared.config.settings import (
    Settings,
)


def create_app(
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build the FastAPI application and wire its dependencies via AppContainer."""
    container = create_app_container(
        settings=settings,
        unit_of_work=unit_of_work,
        llm_client=llm_client,
    )
    return container.fastapi_app


app = create_app()
