"""Integration tests for HTTP Idempotency handling on API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageHandler,
)
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotentCommandExecutor,
)
from src.infrastructure.persistence.in_memory.in_memory_idempotency_repository import (
    InMemoryIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from src.interfaces.http.api import build_api


@pytest.fixture
def app_with_idempotency() -> TestClient:
    uow = InMemoryUnitOfWork()
    idempotency_repo = InMemoryIdempotencyRepositoryAdapter()
    executor = IdempotentCommandExecutor(idempotency_repo=idempotency_repo)

    create_handler = CreateConversationHandler(unit_of_work=uow)
    send_handler = SendMessageHandler(unit_of_work=uow)

    app = build_api(
        create_conversation_handler=create_handler,
        send_message_handler=send_handler,
        idempotent_executor=executor,
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


def test_invalid_idempotency_key_returns_400(app_with_idempotency: TestClient) -> None:
    headers = {"Idempotency-Key": "invalid key with whitespace"}
    resp = app_with_idempotency.post("/conversations", json={"title": "Fail Chat"}, headers=headers)
    assert resp.status_code == 400
