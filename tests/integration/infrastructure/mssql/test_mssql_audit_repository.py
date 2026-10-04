"""Integration tests for MssqlAuditRepositoryAdapter against live SQL Server."""

import pytest
from sqlalchemy.engine import Engine

from src.domain.audit.audit_log_entity import AuditLogRecord
from src.infrastructure.persistence.mssql.audit_repository import (
    MssqlAuditRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.connection import (
    create_session_factory,
)


@pytest.mark.anyio
async def test_mssql_audit_repository_record_and_query_real_db(
    mssql_engine: Engine, clean_db: None
) -> None:
    session_factory = create_session_factory(mssql_engine)

    entry1 = AuditLogRecord.create(
        event_name="llm_token_usage",
        actor_id="usr-int-1",
        resource_type="chat",
        resource_id="conv-int-100",
        action="inference",
        tokens_consumed=250,
        payload={"model": "gpt-4o", "temperature": 0.7},
    )
    entry2 = AuditLogRecord.create(
        event_name="llm_token_usage",
        actor_id="usr-int-1",
        resource_type="chat",
        resource_id="conv-int-200",
        action="inference",
        tokens_consumed=80,
    )

    with session_factory() as session:
        repo = MssqlAuditRepositoryAdapter(session=session)
        await repo.record(entry1)
        await repo.record(entry2)

    with session_factory() as session:
        repo = MssqlAuditRepositoryAdapter(session=session)
        audits = await repo.list_by_resource("chat", "conv-int-100")
        assert len(audits) == 1
        assert audits[0].id == entry1.id
        assert audits[0].tokens_consumed == 250
        assert audits[0].payload == {"model": "gpt-4o", "temperature": 0.7}
