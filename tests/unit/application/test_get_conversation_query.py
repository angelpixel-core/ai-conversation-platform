"""Unit tests for GetConversationQuery and GetConversationQueryHandler (RFC-33)."""

from uuid import uuid4

import pytest

from src.application.conversations.queries.get_conversation import (
    GetConversationQuery,
    GetConversationQueryHandler,
)
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.exceptions import ConversationNotFoundError
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWorkAdapter


def test_get_conversation_returns_messages_and_turn_state() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    conv = Conversation.create("Cloud Budget Audit", tenant_id="corp-acme")
    conv.append_user_message(
        "Estimate Kubernetes cluster cost",
        idempotency_key="4c9d8a1f-3b7e-4a6c-9f8e-1b2c3d4e5f6a",
    )
    with uow:
        uow.conversations.add(conv)
        uow.commit()

    handler = GetConversationQueryHandler(unit_of_work=uow)
    result = handler.handle(
        GetConversationQuery(conversation_id=conv.id, tenant_id="corp-acme")
    )

    assert result.conversation_id == conv.id
    assert result.title == "Cloud Budget Audit"
    assert result.tenant_id == "corp-acme"
    assert result.can_append_user_message is False
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert result.messages[0].content == "Estimate Kubernetes cluster cost"
    assert result.messages[0].idempotency_key == "4c9d8a1f-3b7e-4a6c-9f8e-1b2c3d4e5f6a"
    assert result.messages[0].delivery_status == "DELIVERED"

    # Append assistant message and verify can_append_user_message flips to True
    conv.append_assistant_message("Projected cost is $1,450 USD/month.")
    with uow:
        uow.conversations.add(conv)
        uow.commit()

    result_after = handler.handle(
        GetConversationQuery(conversation_id=conv.id, tenant_id="corp-acme")
    )
    assert result_after.can_append_user_message is True
    assert len(result_after.messages) == 2
    assert result_after.messages[1].role == "assistant"


def test_get_conversation_raises_not_found_for_missing_or_other_tenant() -> None:
    uow = InMemoryUnitOfWorkAdapter()
    conv = Conversation.create("Secret Tenant Chat", tenant_id="corp-acme")
    with uow:
        uow.conversations.add(conv)
        uow.commit()

    handler = GetConversationQueryHandler(unit_of_work=uow)

    with pytest.raises(ConversationNotFoundError):
        handler.handle(GetConversationQuery(conversation_id=uuid4(), tenant_id="corp-acme"))

    with pytest.raises(ConversationNotFoundError):
        handler.handle(GetConversationQuery(conversation_id=conv.id, tenant_id="other-tenant"))

