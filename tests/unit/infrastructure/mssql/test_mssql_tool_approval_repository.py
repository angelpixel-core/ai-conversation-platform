"""Unit tests for MssqlToolApprovalRepository adapter."""

from collections.abc import Iterator

import pytest
from sqlmodel import Session, SQLModel, create_engine
from src.infrastructure.persistence.mssql.mssql_tool_approval_repository import (
    MssqlToolApprovalRepository,
)

from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.value_objects.tool_call import ToolCall


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_mssql_tool_approval_repo_save_and_get(sqlite_session: Session) -> None:
    repo = MssqlToolApprovalRepository(session=sqlite_session)
    tid = TenantId("tenant-acme")
    other_tid = TenantId("tenant-other")

    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 100})
    appr = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )
    repo.save(appr)
    sqlite_session.commit()

    retrieved = repo.get(tid, "appr-1")
    assert retrieved is not None
    assert retrieved.id == "appr-1"
    assert retrieved.tool_call.tool_name == "refund_order"
    assert retrieved.status == ApprovalStatus.PENDING

    # Cross-tenant isolation
    assert repo.get(other_tid, "appr-1") is None


def test_mssql_tool_approval_repo_get_pending(sqlite_session: Session) -> None:
    repo = MssqlToolApprovalRepository(session=sqlite_session)
    tid = TenantId("tenant-acme")

    call1 = ToolCall(call_id="c-1", tool_name="refund_order", arguments={})
    appr1 = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call1,
    )
    call2 = ToolCall(call_id="c-2", tool_name="delete_account", arguments={})
    appr2 = ToolApprovalRequest(
        approval_id="appr-2",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call2,
    )
    appr2.approve(operator_id="op-1")

    repo.save(appr1)
    repo.save(appr2)
    sqlite_session.commit()

    pending = repo.get_pending(tid)
    assert len(pending) == 1
    assert pending[0].id == "appr-1"


def test_mssql_tool_approval_repo_update_resolution(sqlite_session: Session) -> None:
    repo = MssqlToolApprovalRepository(session=sqlite_session)
    tid = TenantId("tenant-acme")

    call = ToolCall(call_id="c-1", tool_name="refund_order", arguments={"amount": 50})
    appr = ToolApprovalRequest(
        approval_id="appr-1",
        tenant_id=tid,
        conversation_id="conv-1",
        tool_call=call,
    )
    repo.save(appr)
    sqlite_session.commit()

    loaded = repo.get(tid, "appr-1")
    assert loaded is not None
    loaded.approve(operator_id="operator-42", justification="Approved by manager")
    repo.save(loaded)
    sqlite_session.commit()

    updated = repo.get(tid, "appr-1")
    assert updated is not None
    assert updated.status == ApprovalStatus.APPROVED
    assert updated.operator_id == "operator-42"
    assert updated.justification == "Approved by manager"
    assert updated.resolved_at is not None
