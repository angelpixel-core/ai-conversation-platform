"""Template canónico para Adaptador de Repositorio de Outbox Relacional con SQLModel.

Reglas:
- Persiste eventos en la tabla física 'outbox_messages'.
- Opera dentro de la misma sesión/transacción de base de datos que el Unit of Work.
- Permite al OutboxDispatcher recuperar y marcar mensajes procesados/fallidos.
"""

from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID
from sqlmodel import Session, select

from src.infrastructure.shared.persistence.outbox.in_memory import OutboxMessage, OutboxStatus
from .models import OutboxMessageModel


class SqlModelOutboxRepository:
    """Adaptador relacional para la persistencia transaccional del patrón Outbox."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, message: OutboxMessage) -> None:
        """Persiste un mensaje de outbox dentro de la transacción activa."""
        model = OutboxMessageModel(
            id=message.id,
            event_type=message.event_type,
            payload=message.payload,
            status=message.status.value,
            created_at=message.created_at,
            processed_at=message.processed_at,
            error_message=message.error_message,
        )
        self._session.add(model)

    def get_pending(self, limit: int = 100) -> Sequence[OutboxMessage]:
        """Recupera los mensajes pendientes de despacho ordenados por fecha."""
        statement = (
            select(OutboxMessageModel)
            .where(OutboxMessageModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxMessageModel.created_at)
            .limit(limit)
        )
        results = self._session.exec(statement).all()
        return [
            OutboxMessage(
                id=m.id,
                event_type=m.event_type,
                payload=m.payload,
                status=OutboxStatus(m.status),
                created_at=m.created_at,
                processed_at=m.processed_at,
                error_message=m.error_message,
            )
            for m in results
        ]

    def mark_as_dispatched(self, message_id: UUID) -> None:
        """Marca un mensaje como exitosamente procesado."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is not None:
            model.status = OutboxStatus.DISPATCHED.value
            model.processed_at = datetime.now(timezone.utc)
            self._session.add(model)

    def mark_as_failed(self, message_id: UUID, error: str) -> None:
        """Marca un mensaje como fallido registrando el error."""
        model = self._session.get(OutboxMessageModel, message_id)
        if model is not None:
            model.status = OutboxStatus.FAILED.value
            model.error_message = error
            self._session.add(model)
