"""Integration tests for HTTP Idempotency handling and RFC-33 contract on API endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.application.conversations.commands.create_conversation import (
    CreateConversationCommandHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageCommandHandler,
)
from src.application.conversations.queries.get_conversation import (
    GetConversationQueryHandler,
)
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotentCommandExecutor,
)
from src.infrastructure.persistence.in_memory.in_memory_idempotency_repository import (
    InMemoryIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter
from src.interfaces.http.api import build_api


@pytest.fixture
def app_with_idempotency() -> TestClient:
    uow = InMemoryUnitOfWorkAdapter()
    idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
    executor = IdempotentCommandExecutor(idempotency_repo=idempotency_repo)

    create_handler = CreateConversationCommandHandler(unit_of_work=uow)
    send_handler = SendMessageCommandHandler(unit_of_work=uow)
    get_handler = GetConversationQueryHandler(unit_of_work=uow)

    app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        get_conversation_handler=get_handler,
        idempotent_executor=executor,
        unit_of_work=uow,
    )
    return TestClient(app)


def test_create_conversation_with_idempotency_key(app_with_idempotency: TestClient) -> None:
    key = "create-conv-idempotency-key-001"
    headers = {"Idempotency-Key": key}

    # 1. First request
    resp1 = app_with_idempotency.post(
        "/conversations", json={"title": "Idempotent Chat"}, headers=headers
    )
    assert resp1.status_code == 201
    body1 = resp1.json()
    assert body1["title"] == "Idempotent Chat"
    assert body1["status"] == "ACTIVE"
    conv_id = body1["id"]

    # 2. Second request with same key
    resp2 = app_with_idempotency.post(
        "/conversations", json={"title": "Idempotent Chat"}, headers=headers
    )
    assert resp2.status_code in (200, 201)
    body2 = resp2.json()
    assert body2["id"] == conv_id
    assert body2["title"] == "Idempotent Chat"


def test_send_message_with_idempotency_key(app_with_idempotency: TestClient) -> None:
    # Create conversation
    create_resp = app_with_idempotency.post(
        "/conversations", json={"title": "Message Idempotency Chat"}
    )
    conv_id = create_resp.json()["id"]

    key = "send-msg-idempotency-key-002"
    headers = {"Idempotency-Key": key}

    # 1. First send
    resp1 = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Important user prompt"},
        headers=headers,
    )
    assert resp1.status_code == 200
    msg1 = resp1.json()
    assert msg1["content"] == "Important user prompt"
    assert msg1["cached"] is False

    # 2. Second send with identical key
    resp2 = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Important user prompt"},
        headers=headers,
    )
    assert resp2.status_code == 200
    msg2 = resp2.json()
    assert msg2["content"] == msg1["content"]
    assert msg2["created_at"] == msg1["created_at"]
    assert msg2["cached"] is True


def test_invalid_idempotency_key_returns_400(app_with_idempotency: TestClient) -> None:
    headers = {"Idempotency-Key": "invalid key with whitespace"}
    resp = app_with_idempotency.post("/conversations", json={"title": "Fail Chat"}, headers=headers)
    assert resp.status_code == 400


def test_rfc33_x_idempotency_key_uuidv4_and_get_conversation(
    app_with_idempotency: TestClient,
) -> None:
    tenant_headers = {"X-Tenant-Id": "tenant-alpha"}
    create_resp = app_with_idempotency.post(
        "/conversations",
        json={"title": "RFC-33 Session"},
        headers=tenant_headers,
    )
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["id"]

    # 1. GET empty conversation -> can_append_user_message is True
    get_resp1 = app_with_idempotency.get(
        f"/conversations/{conv_id}",
        headers=tenant_headers,
    )
    assert get_resp1.status_code == 200
    hist1 = get_resp1.json()
    assert hist1["id"] == conv_id
    assert hist1["tenant_id"] == "tenant-alpha"
    assert hist1["can_append_user_message"] is True
    assert hist1["messages"] == []

    # 2. POST message with valid X-Idempotency-Key (UUIDv4)
    idem_uuid = str(uuid4())
    msg_resp1 = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Hola asistente"},
        headers={**tenant_headers, "X-Idempotency-Key": idem_uuid},
    )
    assert msg_resp1.status_code == 200
    msg1_body = msg_resp1.json()
    assert msg1_body["idempotency_key"] == idem_uuid
    assert msg1_body["cached"] is False

    # 3. Retry with same X-Idempotency-Key and same payload -> 200 OK cached: True
    msg_resp2 = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Hola asistente"},
        headers={**tenant_headers, "X-Idempotency-Key": idem_uuid},
    )
    assert msg_resp2.status_code == 200
    msg2_body = msg_resp2.json()
    assert msg2_body["id"] == msg1_body["id"]
    assert msg2_body["idempotency_key"] == idem_uuid
    assert msg2_body["cached"] is True

    # 4. Retry with same X-Idempotency-Key but mutated payload -> 409 IDEMPOTENCY_PAYLOAD_MISMATCH
    mismatch_resp = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Payload adulterado"},
        headers={**tenant_headers, "X-Idempotency-Key": idem_uuid},
    )
    assert mismatch_resp.status_code == 409
    assert mismatch_resp.json()["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"

    # 5. Consecutive user message with a new key -> 400 TURN_INVARIANT_VIOLATED
    turn_err_resp = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Segundo mensaje consecutivo"},
        headers={**tenant_headers, "X-Idempotency-Key": str(uuid4())},
    )
    assert turn_err_resp.status_code == 400
    assert turn_err_resp.json()["code"] == "TURN_INVARIANT_VIOLATED"

    # 6. Invalid X-Idempotency-Key (not UUIDv4) -> 422 INVALID_UUID_FORMAT
    invalid_uuid_resp = app_with_idempotency.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Test"},
        headers={**tenant_headers, "X-Idempotency-Key": "not-a-uuid-v4"},
    )
    assert invalid_uuid_resp.status_code == 422
    assert invalid_uuid_resp.json()["code"] == "INVALID_UUID_FORMAT"

    # 7. GET conversation after user message -> can_append_user_message is False, 1 message
    get_resp2 = app_with_idempotency.get(
        f"/conversations/{conv_id}",
        headers=tenant_headers,
    )
    assert get_resp2.status_code == 200
    hist2 = get_resp2.json()
    assert hist2["can_append_user_message"] is False
    assert len(hist2["messages"]) == 1
    assert hist2["messages"][0]["id"] == msg1_body["id"]
    assert hist2["messages"][0]["idempotency_key"] == idem_uuid
    assert hist2["messages"][0]["delivery_status"] == "DELIVERED"

    # 8. Cross-tenant GET -> 404 CONVERSATION_NOT_FOUND
    cross_tenant_resp = app_with_idempotency.get(
        f"/conversations/{conv_id}",
        headers={"X-Tenant-Id": "tenant-beta"},
    )
    assert cross_tenant_resp.status_code == 404
    assert cross_tenant_resp.json()["code"] == "CONVERSATION_NOT_FOUND"
