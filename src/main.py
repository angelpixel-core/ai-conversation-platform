"""Application entrypoint.

The composition root lives here so infrastructure choices are explicit and
easy to replace when moving from local adapters to PostgreSQL/MSSQL/Redis/cloud.
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
from src.domain.conversations.ports.conversation_repository import ConversationRepository
from src.infrastructure.llm.fake_llm_client import FakeLlmClientAdapter
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.infrastructure.persistence.mssql import (
    MssqlConversationRepository,
    MssqlUnitOfWork,
    create_mssql_engine,
    create_session_factory,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
    get_settings,
)
from src.interfaces.http.api import build_api


def create_app(
    unit_of_work: UnitOfWork | None = None,
    llm_client: LlmClientPort | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build the FastAPI application and wire its dependencies."""
    read_repo: ConversationRepository | None = None

    if unit_of_work is not None:
        uow = unit_of_work
        try:
            read_repo = uow.conversations
        except RuntimeError:
            session_factory = getattr(uow, "_session_factory", None)
            if session_factory is not None:
                read_repo = MssqlConversationRepository(session=session_factory())
    else:
        app_settings = settings or get_settings()
        if app_settings.PERSISTENCE_DRIVER == PersistenceDriver.MSSQL:
            engine = create_mssql_engine(app_settings.get_database_url())
            session_factory = create_session_factory(engine)
            uow = MssqlUnitOfWork(session_factory=session_factory)
            read_repo = MssqlConversationRepository(session=session_factory())
        else:
            uow = InMemoryUnitOfWork()
            read_repo = uow.conversations

    client = llm_client if llm_client is not None else FakeLlmClientAdapter()

    create_handler = CreateConversationHandler(unit_of_work=uow)
    send_handler = SendMessageHandler(unit_of_work=uow)
    stream_handler = StreamConversationQueryHandler(
        conversation_repository=read_repo,
        llm_client=client,
    )

    return build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        stream_conversation_handler=stream_handler,
    )


app = create_app()
