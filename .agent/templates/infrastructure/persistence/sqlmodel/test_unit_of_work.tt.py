"""Template canónico para Pruebas del Unit of Work Relacional con SQLModel.

Reglas:
- Verifica el ciclo de vida del context manager (__enter__, __exit__).
- Verifica transaccionalidad atómica (commit persiste; rollback descarta).
- Verifica que intentar acceder a repositorios fuera de contexto lance RuntimeError.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.domain.conversations.entities.conversation import Conversation
from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage
from .models import ConversationModel, OutboxMessageModel
from .unit_of_work import SqlModelUnitOfWork


def test_unit_of_work_unstarted_access_raises_runtime_error() -> None:
    engine = create_engine("sqlite:///:memory:")
    uow = SqlModelUnitOfWork(session_factory=lambda: Session(engine))

    with pytest.raises(RuntimeError, match="UnitOfWork has not been started"):
        _ = uow.conversations

    with pytest.raises(RuntimeError, match="UnitOfWork has not been started"):
        _ = uow.outbox


def test_unit_of_work_atomic_commit_persists_conversation_and_outbox() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    uow = SqlModelUnitOfWork(session_factory=lambda: Session(engine))

    conversation = Conversation.create(title="UoW Commit Test")
    outbox = OutboxMessage.create(event_type="ConvCreated", payload='{"id": "123"}')

    with uow:
        uow.conversations.add(conversation)
        uow.outbox.save(outbox)
        uow.commit()

    with Session(engine) as session:
        saved_conv = session.get(ConversationModel, conversation.id)
        saved_outbox = session.get(OutboxMessageModel, outbox.id)

        assert saved_conv is not None
        assert saved_conv.title == "UoW Commit Test"
        assert saved_outbox is not None


def test_unit_of_work_rollback_on_exception_discards_changes() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    uow = SqlModelUnitOfWork(session_factory=lambda: Session(engine))

    conversation = Conversation.create(title="UoW Rollback Test")
    outbox = OutboxMessage.create(event_type="ConvCreated", payload='{}')

    with pytest.raises(ValueError, match="Simulated crash"):
        with uow:
            uow.conversations.add(conversation)
            uow.outbox.save(outbox)
            raise ValueError("Simulated crash")

    with Session(engine) as session:
        assert session.get(ConversationModel, conversation.id) is None
        assert session.get(OutboxMessageModel, outbox.id) is None
