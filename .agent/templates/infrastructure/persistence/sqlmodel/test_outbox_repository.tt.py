"""Template canónico para Pruebas del Repositorio de Outbox Relacional.

Reglas:
- Valida la inserción de eventos en la tabla física outbox_messages.
- Valida recuperación de eventos con status pending en orden cronológico.
- Valida transición de estados a dispatched y failed.
"""

from sqlmodel import Session, SQLModel, create_engine

from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage, OutboxStatus
from .outbox_repository import SqlModelOutboxRepository


def test_outbox_repository_save_and_get_pending() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg = OutboxMessage.create(event_type="MessageAppended", payload='{"text": "hi"}')

    with Session(engine) as session:
        repo = SqlModelOutboxRepository(session=session)
        repo.save(msg)
        session.commit()

    with Session(engine) as session:
        repo = SqlModelOutboxRepository(session=session)
        pending = repo.get_pending()

        assert len(pending) == 1
        assert pending[0].id == msg.id
        assert pending[0].event_type == "MessageAppended"
        assert pending[0].status == OutboxStatus.PENDING


def test_outbox_repository_mark_dispatched_and_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    msg1 = OutboxMessage.create(event_type="Evt1", payload='{}')
    msg2 = OutboxMessage.create(event_type="Evt2", payload='{}')

    with Session(engine) as session:
        repo = SqlModelOutboxRepository(session=session)
        repo.save(msg1)
        repo.save(msg2)
        session.commit()

    with Session(engine) as session:
        repo = SqlModelOutboxRepository(session=session)
        repo.mark_as_dispatched(msg1.id)
        repo.mark_as_failed(msg2.id, error="Broker unreachable")
        session.commit()

    with Session(engine) as session:
        repo = SqlModelOutboxRepository(session=session)
        pending = repo.get_pending()
        assert len(pending) == 0
