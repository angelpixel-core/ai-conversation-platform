"""Unit tests for Tenant-aware LlmMessageProcessingWorker (TDD RED Phase)."""

from collections.abc import AsyncIterator, Mapping, Sequence
from decimal import Decimal

import pytest

from src.application.conversations.workers.llm_message_processing_worker import (
    LlmMessageProcessingWorker,
)
from src.application.shared.ports.llm_client import LlmClientPort
from src.application.shared.tenancy.tenant_context import get_current_tenant_id
from src.application.tenants.commands.settle_quota_command import SettleQuotaCommandHandler
from src.domain.conversations.entities.conversation import Conversation
from src.domain.shared.events.event_envelope import EventEnvelope
from src.domain.tenants.entities.tenant import Tenant
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork


class ContextInspectingLlmClient(LlmClientPort):
    """LLM client that captures the active TenantContext during streaming."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.captured_tenant_id: str | None = None

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        self.captured_tenant_id = get_current_tenant_id()
        for token in self.tokens:
            yield token


class FailingLlmClient(LlmClientPort):
    """LLM client that fails to trigger fallback logic."""

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        raise ConnectionError("Primary provider 503 Overloaded")
        yield ""  # pragma: no cover


class FallbackLlmClient(LlmClientPort):
    """Contingency LLM client producing tokens upon primary failure."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    async def stream_chat(
        self,
        messages: Sequence[Mapping[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        for token in self.tokens:
            yield token


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def active_conversation(uow: InMemoryUnitOfWork) -> Conversation:
    conversation = Conversation.create(title="Tenant Support")
    conversation.append_user_message("Need billing report")
    uow.conversations.add(conversation)
    uow.commit()
    return conversation


@pytest.mark.anyio
async def test_worker_propagates_tenant_context_during_inference(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    llm = ContextInspectingLlmClient(["Your ", "report ", "is ready."])
    worker = LlmMessageProcessingWorker(unit_of_work=uow, llm_client=llm)

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "tenant_id": "tenant-enterprise-99",
            "message": {"role": "user", "content": "Need billing report"},
        },
    )

    await worker.handle(envelope)

    assert llm.captured_tenant_id == "tenant-enterprise-99"
    # Ensure context is reset after worker execution
    assert get_current_tenant_id() is None


@pytest.mark.anyio
async def test_worker_settles_quota_after_inference(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    # 1. Setup tenant with $100 balance and $10 reserved
    tenant = Tenant(
        tenant_id=TenantId("tenant-billable"),
        name="Billable Tenant",
        budget=MonetaryBudget(balance=Decimal("100.00"), reserved_amount=Decimal("10.00")),
    )
    uow.tenants.add(tenant)

    llm = ContextInspectingLlmClient(["token1", "token2", "token3"])
    settle_handler = SettleQuotaCommandHandler(unit_of_work=uow)

    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=llm,
        settle_handler=settle_handler,
        cost_per_token=Decimal("0.50"),
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "tenant_id": "tenant-billable",
            "reserved_cost": "10.00",
            "message": {"role": "user", "content": "Need billing report"},
        },
    )

    await worker.handle(envelope)

    # 3 tokens * $0.50 = $1.50 actual cost
    # Balance: $100 - $1.50 = $98.50, reserved was cleared ($0.00)
    updated_tenant = uow.tenants.get(TenantId("tenant-billable"))
    assert updated_tenant is not None
    assert updated_tenant.budget.balance == Decimal("98.50")
    assert updated_tenant.budget.reserved_amount == Decimal("0.00")


@pytest.mark.anyio
async def test_worker_fallback_llm_on_primary_failure(
    uow: InMemoryUnitOfWork, active_conversation: Conversation
) -> None:
    primary_llm = FailingLlmClient()
    fallback_llm = FallbackLlmClient(["Fallback ", "response ", "delivered."])

    worker = LlmMessageProcessingWorker(
        unit_of_work=uow,
        llm_client=primary_llm,
        fallback_llm_client=fallback_llm,
    )

    envelope = EventEnvelope.create(
        event_type="MessageAppendedDomainEvent",
        payload={
            "conversation_id": str(active_conversation.id),
            "tenant_id": "tenant-fallback-user",
            "message": {"role": "user", "content": "Need billing report"},
        },
    )

    await worker.handle(envelope)

    updated_conv = uow.conversations.get(active_conversation.id)
    assert updated_conv is not None
    assert len(updated_conv.messages) == 2
    assert updated_conv.messages[1].content == "Fallback response delivered."
