"""MSSQL Audit Repository adapter using SQLModel."""

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager

from sqlmodel import Session, select

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.infrastructure.persistence.mssql.models import AuditLogModel


class MssqlAuditRepository(AuditRepositoryPort):
    """Relational adapter for audit log persistence backed by SQLModel."""

    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        if callable(self._session_or_factory):
            with self._session_or_factory() as session:
                yield session
        else:
            yield self._session_or_factory

    async def record(self, log_entry: AuditLogRecord) -> None:
        model = AuditLogModel(
            id=log_entry.id,
            event_name=log_entry.event_name,
            actor_id=log_entry.actor_id,
            resource_type=log_entry.resource_type,
            resource_id=log_entry.resource_id,
            action=log_entry.action,
            tokens_consumed=log_entry.tokens_consumed,
            payload_json=json.dumps(log_entry.payload) if log_entry.payload else None,
            occurred_at=log_entry.occurred_at,
        )
        with self._get_session() as session:
            session.add(model)
            session.commit()

    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditLogRecord]:
        stmt = (
            select(AuditLogModel)
            .where(
                AuditLogModel.resource_type == resource_type,
                AuditLogModel.resource_id == resource_id,
            )
            .order_by(AuditLogModel.occurred_at.asc())  # type: ignore[attr-defined]
        )
        with self._get_session() as session:
            results = session.exec(stmt).all()
            return [
                AuditLogRecord(
                    id=m.id,
                    event_name=m.event_name,
                    actor_id=m.actor_id,
                    resource_type=m.resource_type,
                    resource_id=m.resource_id,
                    action=m.action,
                    tokens_consumed=m.tokens_consumed,
                    payload=json.loads(m.payload_json) if m.payload_json else {},
                    occurred_at=m.occurred_at,
                )
                for m in results
            ]


# Canonical adapter alias conforming to <Technology><Port>Adapter
MssqlAuditRepositoryAdapter = MssqlAuditRepository
