"""Application entrypoint.

The composition root lives here so infrastructure choices are explicit and
easy to replace when moving from local adapters to PostgreSQL/Redis/cloud.
"""

from fastapi import FastAPI

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


def create_app() -> FastAPI:
    """Build the FastAPI application and wire its dependencies."""
    unit_of_work = InMemoryUnitOfWork()
    handler = CreateConversationHandler(unit_of_work=unit_of_work)
    app = build_api(handler=handler)
    return app


app = create_app()
