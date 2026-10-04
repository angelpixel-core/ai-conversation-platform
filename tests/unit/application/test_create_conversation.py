from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationCommandHandler,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_create_conversation_persists_aggregate() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    handler = CreateConversationCommandHandler(uow)

    result = handler.handle(CreateConversationCommand("Demo conversation"))

    stored = uow.conversations.get(result.conversation_id)
    assert stored is not None
    assert stored.title == "Demo conversation"
