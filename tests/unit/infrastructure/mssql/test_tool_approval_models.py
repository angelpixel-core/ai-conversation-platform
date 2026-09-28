"""Unit tests for MSSQL ToolApprovalModel and ToolExecutionAuditModel."""

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.infrastructure.persistence.mssql.models import (
    ToolApprovalModel,
    ToolExecutionAuditModel,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_tool_approval_model_persistence(sqlite_session: Session) -> None:
    model = ToolApprovalModel(
        id="appr-123",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        call_id="call-99",
        tool_name="refund_order",
        arguments_json='{"order_id": "ord-1", "amount": 100.0}',
        status="PENDING",
        operator_id=None,
        justification=None,
    )
    sqlite_session.add(model)
    sqlite_session.commit()

    retrieved = sqlite_session.exec(
        select(ToolApprovalModel).where(ToolApprovalModel.id == "appr-123")
    ).first()

    assert retrieved is not None
    assert retrieved.id == "appr-123"
    assert retrieved.tenant_id == "corp-acme"
    assert retrieved.tool_name == "refund_order"
    assert retrieved.status == "PENDING"
    assert retrieved.operator_id is None
    assert isinstance(retrieved.created_at, datetime)
    assert retrieved.resolved_at is None


def test_tool_execution_audit_model_persistence(sqlite_session: Session) -> None:
    audit = ToolExecutionAuditModel(
        id="audit-1",
        tenant_id="corp-acme",
        conversation_id="conv-1",
        call_id="call-99",
        tool_name="get_weather",
        arguments_json='{"city": "Paris"}',
        output_json='{"temp": "18°C"}',
        is_error=False,
        execution_time_ms=25.4,
    )
    sqlite_session.add(audit)
    sqlite_session.commit()

    retrieved = sqlite_session.exec(
        select(ToolExecutionAuditModel).where(ToolExecutionAuditModel.id == "audit-1")
    ).first()

    assert retrieved is not None
    assert retrieved.id == "audit-1"
    assert retrieved.tenant_id == "corp-acme"
    assert retrieved.tool_name == "get_weather"
    assert retrieved.is_error is False
    assert retrieved.execution_time_ms == 25.4
    assert isinstance(retrieved.created_at, datetime)
