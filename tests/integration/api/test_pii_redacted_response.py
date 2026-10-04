"""Integration test: Sensitive PII automatically redacted before storage and inference."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationCommandHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageCommandHandler,
)
from src.application.governance.services.guardrail_pipeline_service import (
    SafetyGuardrailPipelineService,
)
from src.application.shared.governance.guarded_command_executor import (
    GuardedCommandExecutor,
)
from src.infrastructure.governance.heuristic_injection_detector_adapter import (
    HeuristicInjectionDetectorAdapter,
)
from src.infrastructure.governance.regex_pii_scanner_adapter import (
    RegexPiiScannerAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_incident_repository import (
    InMemoryIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import (
    InMemoryUnitOfWorkAdapter,
)
from src.interfaces.http.api import build_api


@pytest.fixture
def client_and_repo() -> tuple[AsyncClient, InMemoryUnitOfWorkAdapter]:
    uow = InMemoryUnitOfWorkAdapter()
    incident_repo = InMemoryIncidentRepositoryAdapter()
    pipeline = SafetyGuardrailPipelineService(
        safety_guardrail=HeuristicInjectionDetectorAdapter(),
        pii_scanner=RegexPiiScannerAdapter(),
    )
    guarded_executor = GuardedCommandExecutor(
        pipeline=pipeline,
        incident_repo=incident_repo,
    )
    create_handler = CreateConversationCommandHandler(uow)
    send_handler = SendMessageCommandHandler(uow)

    app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        guarded_executor=guarded_executor,
    )
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, uow


@pytest.mark.anyio
async def test_pii_redacted_in_message_payload(
    client_and_repo: tuple[AsyncClient, InMemoryUnitOfWorkAdapter],
) -> None:
    client, uow = client_and_repo
    create_res = CreateConversationCommandHandler(uow).handle(
        CreateConversationCommand(title="PII Redaction Test")
    )
    conv_id = create_res.conversation_id

    pii_payload = {
        "content": (
            "My private email is sensitive@finance.acme.com and credit card is 4532-0150-1234-5671."
        )
    }

    response = await client.post(
        f"/conversations/{conv_id}/messages",
        json=pii_payload,
        headers={"x-tenant-id": "corp-acme"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "[REDACTED_EMAIL]" in data["content"]
    assert "[REDACTED_CREDIT_CARD]" in data["content"]
    assert "sensitive@finance.acme.com" not in data["content"]
    assert "4532-0150-1234-5671" not in data["content"]

    # Verify state in repository
    with uow:
        conv = uow.conversations.get(conv_id)
        assert conv is not None
        user_msg = conv.messages[-1]
        assert "[REDACTED_EMAIL]" in user_msg.content
        assert "[REDACTED_CREDIT_CARD]" in user_msg.content
