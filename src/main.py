"""Application entrypoint.

The composition root lives here so infrastructure choices are explicit and
easy to replace when moving from local adapters to PostgreSQL/Redis/cloud.
"""

from fastapi import FastAPI

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.ports.unit_of_work import UnitOfWork
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


def create_app(
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
) -> FastAPI:
    """Build the FastAPI application and wire its dependencies."""
    uow = unit_of_work if unit_of_work is not None else InMemoryUnitOfWork()
    client = llm_client if llm_client is not None else FakeLlmClientAdapter()

    create_handler = CreateConversationHandler(unit_of_work=uow)
    send_handler = SendMessageHandler(unit_of_work=uow)
    stream_handler = StreamConversationQueryHandler(unit_of_work=uow, llm_client=client)

    return build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
    )


app = create_app()
