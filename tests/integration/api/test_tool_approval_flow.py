"""Integration tests for Human-in-the-Loop tool approvals HTTP flow (Phase 5 RED)."""

from collections.abc import AsyncIterator, Mapping, Sequence
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.value_objects.tool_call import ToolCall
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


class StubLlmClient(LlmClientPort):
    """Stub LLM client producing tokens."""

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        for token in ["Executing ", "approved ", "operation."]:
            yield token


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.mark.anyio
async def test_get_pending_approvals_endpoint(uow: InMemoryUnitOfWork) -> None:
    app = build_api(unit_of_work=uow)
    tenant_id = TenantId("corp-acme")
    conv_id = uuid4()

    approval = ToolApprovalRequest.create(
        approval_id="appr-100",
        tenant_id=tenant_id,
        conversation_id=str(conv_id),
        tool_call=ToolCall(
            call_id="call-1",
            tool_name="database_migrate",
            arguments={"version": "v2.0"},
        ),
    )
    with uow:
        uow.tool_approvals.save(approval)
        uow.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch pending for corp-acme
        response = await client.get("/tenants/corp-acme/approvals/pending")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["approval_id"] == "appr-100"
        assert items[0]["tenant_id"] == "corp-acme"
        assert items[0]["tool_name"] == "database_migrate"
        assert items[0]["arguments"] == {"version": "v2.0"}
        assert items[0]["status"] == "PENDING"

        # 2. Fetch pending for other tenant -> empty list
        other_resp = await client.get("/tenants/corp-other/approvals/pending")
        assert other_resp.status_code == 200
        assert other_resp.json() == []


@pytest.mark.anyio
async def test_approve_tool_decision_endpoint(uow: InMemoryUnitOfWork) -> None:
    app = build_api(unit_of_work=uow)
    tenant_id = TenantId("corp-acme")
    conv_id = uuid4()

    approval = ToolApprovalRequest.create(
        approval_id="appr-200",
        tenant_id=tenant_id,
        conversation_id=str(conv_id),
        tool_call=ToolCall(
            call_id="call-2",
            tool_name="send_payment",
            arguments={"amount": 5000},
        ),
    )
    with uow:
        uow.tool_approvals.save(approval)
        uow.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tenants/corp-acme/approvals/appr-200/decision",
            json={
                "decision": "approve",
                "resolved_by": "sec-officer@corp.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == "appr-200"
        assert data["status"] == "APPROVED"
        assert data["resolved_by"] == "sec-officer@corp.com"
        assert data["resolved_at"] is not None

    with uow:
        saved = uow.tool_approvals.get(tenant_id, "appr-200")
        assert saved is not None
        assert saved.status == ApprovalStatus.APPROVED
        assert saved.operator_id == "sec-officer@corp.com"


@pytest.mark.anyio
async def test_reject_tool_decision_endpoint(uow: InMemoryUnitOfWork) -> None:
    app = build_api(unit_of_work=uow)
    tenant_id = TenantId("corp-acme")
    conv_id = uuid4()

    approval = ToolApprovalRequest.create(
        approval_id="appr-300",
        tenant_id=tenant_id,
        conversation_id=str(conv_id),
        tool_call=ToolCall(
            call_id="call-3",
            tool_name="delete_account",
            arguments={"account_id": "acc-9"},
        ),
    )
    with uow:
        uow.tool_approvals.save(approval)
        uow.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tenants/corp-acme/approvals/appr-300/decision",
            json={
                "decision": "reject",
                "resolved_by": "compliance@corp.com",
                "reason": "Missing secondary verification",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approval_id"] == "appr-300"
        assert data["status"] == "REJECTED"
        assert data["resolved_by"] == "compliance@corp.com"
        assert data["rejection_reason"] == "Missing secondary verification"

    with uow:
        saved = uow.tool_approvals.get(tenant_id, "appr-300")
        assert saved is not None
        assert saved.status == ApprovalStatus.REJECTED
        assert saved.operator_id == "compliance@corp.com"
        assert saved.justification == "Missing secondary verification"


@pytest.mark.anyio
async def test_cross_tenant_approval_isolation_returns_404(
    uow: InMemoryUnitOfWork,
) -> None:
    app = build_api(unit_of_work=uow)
    tenant_id = TenantId("corp-acme")
    conv_id = uuid4()

    approval = ToolApprovalRequest.create(
        approval_id="appr-400",
        tenant_id=tenant_id,
        conversation_id=str(conv_id),
        tool_call=ToolCall(
            call_id="call-4",
            tool_name="drop_table",
            arguments={"table": "users"},
        ),
    )
    with uow:
        uow.tool_approvals.save(approval)
        uow.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tenants/other-corp/approvals/appr-400/decision",
            json={"decision": "approve", "resolved_by": "attacker@evil.com"},
        )
        assert response.status_code == 404


@pytest.mark.anyio
async def test_sse_stream_emits_tool_approval_required_event(
    uow: InMemoryUnitOfWork,
) -> None:
    llm_client = StubLlmClient()
    stream_handler = StreamConversationQueryHandler(
        unit_of_work=uow,
        llm_client=llm_client,
    )
    app = build_api(
        unit_of_work=uow,
        stream_conversation_handler=stream_handler,
    )

    tenant_id = TenantId("corp-acme")
    conv = Conversation.create(title="HITL conversation")
    conv.append_user_message("Transfer $10,000 to external account")
    conv_id = conv.id

    approval = ToolApprovalRequest.create(
        approval_id="appr-500",
        tenant_id=tenant_id,
        conversation_id=str(conv_id),
        tool_call=ToolCall(
            call_id="call-5",
            tool_name="wire_transfer",
            arguments={"amount": 10000},
        ),
    )

    with uow:
        uow.conversations.add(conv)
        uow.tool_approvals.save(approval)
        uow.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/conversations/{conv_id}/stream",
            headers={"X-Tenant-Id": "corp-acme"},
        )
        assert response.status_code == 200
        body_text = response.text
        assert "event: tool_approval_required" in body_text
        assert "wire_transfer" in body_text
        assert "appr-500" in body_text
