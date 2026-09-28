"""MSSQL Idempotency Repository adapter using SQLModel."""

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRecord,
    IdempotencyRepositoryPort,
    IdempotencyStatus,
)
from src.infrastructure.persistence.mssql.models import IdempotencyRecordModel


class MssqlIdempotencyRepository(IdempotencyRepositoryPort):
    """Relational adapter for idempotency persistence backed by SQLModel."""

    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        if callable(self._session_or_factory):
            with self._session_or_factory() as session:
                yield session
        else:
            yield self._session_or_factory

    async def try_acquire(self, key: str, ttl_seconds: int = 120) -> bool:
        with self._get_session() as session:
            existing = session.get(IdempotencyRecordModel, key)
            if existing is not None:
                return False

            now = datetime.now(UTC)
            record = IdempotencyRecordModel(
                key=key,
                status=IdempotencyStatus.PENDING.value,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.commit()
            return True

    async def get(self, key: str) -> IdempotencyRecord | None:
        with self._get_session() as session:
            model = session.get(IdempotencyRecordModel, key)
            if model is None:
                return None
            return IdempotencyRecord(
                key=model.key,
                status=IdempotencyStatus(model.status),
                response_code=model.response_code,
                response_body=json.loads(model.response_body) if model.response_body else None,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    async def mark_completed(
        self, key: str, response_code: int, response_body: dict[str, Any]
    ) -> None:
        with self._get_session() as session:
            model = session.get(IdempotencyRecordModel, key)
            if model is not None:
                model.status = IdempotencyStatus.COMPLETED.value
                model.response_code = response_code
                model.response_body = json.dumps(response_body)
                model.updated_at = datetime.now(UTC)
                session.add(model)
                session.commit()

    async def mark_failed(self, key: str, error_message: str) -> None:
        with self._get_session() as session:
            model = session.get(IdempotencyRecordModel, key)
            if model is not None:
                model.status = IdempotencyStatus.FAILED.value
                model.response_body = json.dumps({"error": error_message})
                model.updated_at = datetime.now(UTC)
                session.add(model)
                session.commit()
