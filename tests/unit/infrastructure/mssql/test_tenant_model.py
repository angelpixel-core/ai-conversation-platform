"""Unit tests for MSSQL TenantModel and TenantPolicyModel."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from src.infrastructure.persistence.mssql.models import (
    AuditLogModel,
    ConversationModel,
    StreamBufferChunkModel,
    TenantModel,
    TenantPolicyModel,
)


@pytest.fixture(name="sqlite_session")
def fixture_sqlite_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_tenant_model_instantiation() -> None:
    tenant = TenantModel(
        id="acme-corp",
        name="Acme Corporation",
        balance_usd=Decimal("150.5000"),
        reserved_usd=Decimal("20.0000"),
        currency="USD",
    )
    assert tenant.id == "acme-corp"
    assert tenant.name == "Acme Corporation"
    assert tenant.balance_usd == Decimal("150.5000")
    assert tenant.reserved_usd == Decimal("20.0000")
    assert tenant.status == "ACTIVE"
    assert tenant.currency == "USD"
    assert isinstance(tenant.created_at, datetime)
    assert isinstance(tenant.updated_at, datetime)


def test_tenant_policy_model_instantiation() -> None:
    policy = TenantPolicyModel(
        tenant_id="acme-corp",
        tier="ENTERPRISE",
        max_tokens_per_request=8192,
        monthly_budget_usd=Decimal("500.0000"),
        allowed_models_json='["gpt-4o", "gemini-1.5-pro"]',
    )
    assert policy.tenant_id == "acme-corp"
    assert policy.tier == "ENTERPRISE"
    assert policy.max_tokens_per_request == 8192
    assert policy.monthly_budget_usd == Decimal("500.0000")
    assert policy.allowed_models_json == '["gpt-4o", "gemini-1.5-pro"]'


def test_tenant_and_policy_persistence(sqlite_session: Session) -> None:
    tenant = TenantModel(
        id="nexus-ai",
        name="Nexus AI Inc",
        balance_usd=Decimal("250.0000"),
        reserved_usd=Decimal("10.0000"),
    )
    policy = TenantPolicyModel(
        tenant_id="nexus-ai",
        tier="ENTERPRISE",
        max_tokens_per_request=16384,
        monthly_budget_usd=Decimal("1000.0000"),
        allowed_models_json='["gpt-4o", "claude-3-5-sonnet"]',
    )
    tenant.policy = policy

    sqlite_session.add(tenant)
    sqlite_session.commit()

    saved_tenant = sqlite_session.get(TenantModel, "nexus-ai")
    assert saved_tenant is not None
    assert saved_tenant.name == "Nexus AI Inc"
    assert saved_tenant.balance_usd == Decimal("250.0000")
    assert saved_tenant.policy is not None
    assert saved_tenant.policy.tier == "ENTERPRISE"
    assert saved_tenant.policy.max_tokens_per_request == 16384


def test_models_have_tenant_id_discriminator_column(sqlite_session: Session) -> None:
    conv = ConversationModel(
        id=uuid4(),
        title="Multi-tenant test conversation",
        tenant_id="tenant-alpha",
    )
    audit = AuditLogModel(
        id=uuid4(),
        event_name="quota_reserved",
        actor_id="usr-1",
        resource_type="tenant",
        resource_id="tenant-alpha",
        action="reserve",
        tenant_id="tenant-alpha",
        occurred_at=datetime.now(UTC),
    )
    chunk = StreamBufferChunkModel(
        id="chk-1",
        stream_id="strm-1",
        sequence_number=1,
        content="hello",
        tenant_id="tenant-alpha",
    )

    sqlite_session.add(conv)
    sqlite_session.add(audit)
    sqlite_session.add(chunk)
    sqlite_session.commit()

    saved_conv = sqlite_session.exec(
        select(ConversationModel).where(ConversationModel.tenant_id == "tenant-alpha")
    ).first()
    assert saved_conv is not None
    assert saved_conv.tenant_id == "tenant-alpha"

    saved_audit = sqlite_session.exec(
        select(AuditLogModel).where(AuditLogModel.tenant_id == "tenant-alpha")
    ).first()
    assert saved_audit is not None
    assert saved_audit.tenant_id == "tenant-alpha"

    saved_chunk = sqlite_session.exec(
        select(StreamBufferChunkModel).where(StreamBufferChunkModel.tenant_id == "tenant-alpha")
    ).first()
    assert saved_chunk is not None
    assert saved_chunk.tenant_id == "tenant-alpha"
