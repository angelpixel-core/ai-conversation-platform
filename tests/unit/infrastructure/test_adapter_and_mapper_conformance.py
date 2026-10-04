"""Unit tests verifying adapter and mapper standardization across the infrastructure layer."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.application.shared.ports.event_consumer_port import EventConsumerPort
from src.application.shared.ports.http_client import HttpClientPort
from src.application.shared.ports.idempotency_repository_port import (
    IdempotencyRepositoryPort,
)
from src.application.shared.ports.message_broker_port import MessageBrokerPort
from src.application.shared.ports.stream_buffer_repository_port import (
    StreamBufferRepositoryPort,
)
from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.domain.audit.ports.audit_repository_port import AuditRepositoryPort
from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepositoryPort,
)
from src.domain.governance.entities.security_incident import SecurityIncident
from src.domain.governance.ports.incident_repository_port import IncidentRepositoryPort
from src.domain.governance.value_objects.incident_severity import IncidentSeverity
from src.domain.knowledge.entities.document import Document, DocumentStatus
from src.domain.knowledge.ports.knowledge_repository_port import KnowledgeRepositoryPort
from src.domain.tenants.entities.tenant import Tenant, TenantStatus
from src.domain.tenants.entities.tenant_policy import TenantPolicy, TenantTier
from src.domain.tenants.ports.tenant_repository_port import TenantRepositoryPort
from src.domain.tenants.value_objects.monetary_budget import MonetaryBudget
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.domain.tools.entities.tool_approval_request import (
    ApprovalStatus,
    ToolApprovalRequest,
)
from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.domain.tools.value_objects.tool_call import ToolCall
from src.infrastructure.governance.anyio_stream_guardrail_filter import (
    AnyioStreamGuardrailFilterAdapter,
)
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBrokerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMQPublisherAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_audit_repository import (
    InMemoryAuditRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_idempotency_repository import (
    InMemoryIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_incident_repository import (
    InMemoryIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_stream_buffer_repository import (
    InMemoryStreamBufferRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_tool_approval_repository import (
    InMemoryToolApprovalRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.knowledge_repository import (
    InMemoryKnowledgeRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.repository import (
    InMemoryConversationRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.tenant_repository import (
    InMemoryTenantRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import (
    InMemoryUnitOfWorkAdapter,
)
from src.infrastructure.persistence.mssql.audit_repository import (
    MssqlAuditRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.governance_mapper import (
    GovernanceMapper,
)
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.knowledge_mapper import (
    KnowledgeMapper,
)
from src.infrastructure.persistence.mssql.mapper import (
    ConversationMapper,
)
from src.infrastructure.persistence.mssql.models import (
    ConversationModel,
    DocumentModel,
    SecurityIncidentModel,
    TenantModel,
    ToolApprovalModel,
)
from src.infrastructure.persistence.mssql.mssql_incident_repository import (
    MssqlIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_knowledge_repository import (
    MssqlKnowledgeRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_tool_approval_repository import (
    MssqlToolApprovalRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_workflow_checkpoint_repository import (
    MssqlWorkflowCheckpointRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.outbox_repository import (
    MssqlOutboxRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.repository import (
    MssqlConversationRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.tenant_mapper import (
    TenantMapper,
)
from src.infrastructure.persistence.mssql.tenant_repository import (
    MssqlTenantRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.tool_approval_mapper import (
    ToolApprovalMapper,
)
from src.infrastructure.persistence.mssql.unit_of_work import (
    MssqlUnitOfWorkAdapter,
)
from src.infrastructure.persistence.mssql.workflow_mapper import (
    WorkflowMapper,
)
from src.infrastructure.shared.http_client.httpx_client import (
    HttpxHttpClientAdapter,
)
from src.infrastructure.shared.persistence.outbox.dispatcher import (
    OutboxDispatcherAdapter,
)
from src.infrastructure.shared.persistence.outbox.in_memory import (
    InMemoryOutboxRepositoryAdapter,
)
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunnerAdapter,
)


class TestMapperConformance:
    """Verifies that all mappers expose standard to_domain and to_persistence methods."""

    def test_should_expose_to_domain_and_to_persistence_on_conversation_mapper(self) -> None:
        assert hasattr(ConversationMapper, "to_domain") and callable(ConversationMapper.to_domain)
        assert hasattr(ConversationMapper, "to_persistence") and callable(
            ConversationMapper.to_persistence
        )

        conv = Conversation.create("Test Conversation")
        model = ConversationMapper.to_persistence(conv)
        assert isinstance(model, ConversationModel)
        reconstituted = ConversationMapper.to_domain(model)
        assert reconstituted.id == conv.id
        assert reconstituted.title == conv.title

    def test_should_expose_to_domain_and_to_persistence_on_tenant_mapper(self) -> None:
        assert hasattr(TenantMapper, "to_domain") and callable(TenantMapper.to_domain)
        assert hasattr(TenantMapper, "to_persistence") and callable(TenantMapper.to_persistence)

        tenant = Tenant(
            tenant_id=TenantId("tenant-test"),
            name="Test Corp",
            budget=MonetaryBudget(balance=Decimal("100.00"), currency="USD"),
            policy=TenantPolicy(
                tier=TenantTier.ENTERPRISE,
                max_tokens_per_request=8192,
                monthly_budget_usd=Decimal("500.00"),
                allowed_models=frozenset({"gpt-4o"}),
            ),
            status=TenantStatus.ACTIVE,
        )
        model = TenantMapper.to_persistence(tenant)
        assert isinstance(model, TenantModel)
        reconstituted = TenantMapper.to_domain(model)
        assert reconstituted.id == tenant.id
        assert reconstituted.name == tenant.name

    def test_should_expose_to_domain_and_to_persistence_on_knowledge_mapper(self) -> None:
        assert hasattr(KnowledgeMapper, "to_domain") and callable(KnowledgeMapper.to_domain)
        assert hasattr(KnowledgeMapper, "to_persistence") and callable(
            KnowledgeMapper.to_persistence
        )

        doc = Document.create(
            document_id="doc-k-1",
            tenant_id=TenantId("tenant-k"),
            filename="guide.pdf",
            content_type="application/pdf",
        )
        model = KnowledgeMapper.to_persistence(doc)
        assert isinstance(model, DocumentModel)
        reconstituted = KnowledgeMapper.to_domain(model)
        assert reconstituted.id == doc.id
        assert reconstituted.status == DocumentStatus.PENDING

    def test_should_expose_to_domain_and_to_persistence_on_tool_approval_mapper(self) -> None:
        assert hasattr(ToolApprovalMapper, "to_domain") and callable(ToolApprovalMapper.to_domain)
        assert hasattr(ToolApprovalMapper, "to_persistence") and callable(
            ToolApprovalMapper.to_persistence
        )

        request = ToolApprovalRequest(
            approval_id="app-1",
            tenant_id=TenantId("tenant-t"),
            conversation_id=str(uuid4()),
            tool_call=ToolCall(call_id="call-1", tool_name="bash", arguments={"cmd": "ls"}),
            status=ApprovalStatus.PENDING,
        )
        model = ToolApprovalMapper.to_persistence(request)
        assert isinstance(model, ToolApprovalModel)
        reconstituted = ToolApprovalMapper.to_domain(model)
        assert reconstituted.id == request.id
        assert reconstituted.status == ApprovalStatus.PENDING

    def test_should_expose_to_domain_and_to_persistence_on_governance_mapper(self) -> None:
        assert hasattr(GovernanceMapper, "to_domain") and callable(GovernanceMapper.to_domain)
        assert hasattr(GovernanceMapper, "to_persistence") and callable(
            GovernanceMapper.to_persistence
        )

        incident = SecurityIncident(
            incident_id="inc-1",
            tenant_id=TenantId("tenant-g"),
            severity=IncidentSeverity.CRITICAL,
            rule_name="sql_injection",
            description="Detected injection attempt",
            prompt_preview="DROP TABLE",
            details={"ip": "127.0.0.1"},
            created_at=datetime.now(UTC),
        )
        model = GovernanceMapper.to_persistence(incident)
        assert isinstance(model, SecurityIncidentModel)
        reconstituted = GovernanceMapper.to_domain(model)
        assert reconstituted.id == incident.id
        assert reconstituted.severity == IncidentSeverity.CRITICAL

    def test_should_expose_to_domain_and_to_persistence_on_workflow_mapper(self) -> None:
        assert hasattr(WorkflowMapper, "to_domain") and callable(WorkflowMapper.to_domain)
        assert hasattr(WorkflowMapper, "to_persistence") and callable(WorkflowMapper.to_persistence)


class TestAdapterNamingAndPortConformance:
    """Verifies that canonical <Technology><Port>Adapter classes satisfy their respective ports."""

    def test_mssql_adapters_satisfy_ports(self) -> None:
        assert issubclass(MssqlConversationRepositoryAdapter, ConversationRepositoryPort)
        assert issubclass(MssqlTenantRepositoryAdapter, TenantRepositoryPort)
        assert issubclass(MssqlIncidentRepositoryAdapter, IncidentRepositoryPort)
        assert issubclass(MssqlKnowledgeRepositoryAdapter, KnowledgeRepositoryPort)
        assert issubclass(MssqlToolApprovalRepositoryAdapter, ToolApprovalRepositoryPort)
        assert issubclass(MssqlAuditRepositoryAdapter, AuditRepositoryPort)
        assert issubclass(MssqlIdempotencyRepositoryAdapter, IdempotencyRepositoryPort)
        assert issubclass(MssqlStreamBufferRepositoryAdapter, StreamBufferRepositoryPort)
        assert issubclass(MssqlUnitOfWorkAdapter, UnitOfWorkPort)
        assert hasattr(MssqlWorkflowCheckpointRepositoryAdapter, "save_checkpoint")
        assert hasattr(MssqlOutboxRepositoryAdapter, "save")

    def test_in_memory_adapters_satisfy_ports(self) -> None:
        assert issubclass(InMemoryConversationRepositoryAdapter, ConversationRepositoryPort)
        assert issubclass(InMemoryTenantRepositoryAdapter, TenantRepositoryPort)
        assert issubclass(InMemoryIncidentRepositoryAdapter, IncidentRepositoryPort)
        assert issubclass(InMemoryKnowledgeRepositoryAdapter, KnowledgeRepositoryPort)
        assert issubclass(InMemoryToolApprovalRepositoryAdapter, ToolApprovalRepositoryPort)
        assert issubclass(InMemoryAuditRepositoryAdapter, AuditRepositoryPort)
        assert issubclass(InMemoryIdempotencyRepositoryAdapter, IdempotencyRepositoryPort)
        assert issubclass(InMemoryStreamBufferRepositoryAdapter, StreamBufferRepositoryPort)
        assert issubclass(InMemoryUnitOfWorkAdapter, UnitOfWorkPort)
        assert issubclass(InMemoryMessageBrokerAdapter, MessageBrokerPort)
        assert issubclass(InMemoryMessageBrokerAdapter, EventConsumerPort)
        assert hasattr(InMemoryOutboxRepositoryAdapter, "save")
        assert hasattr(OutboxDispatcherAdapter, "dispatch_pending")

    def test_messaging_and_tools_adapters_satisfy_ports(self) -> None:
        assert issubclass(RabbitMQPublisherAdapter, MessageBrokerPort)
        assert issubclass(RabbitMQConsumerAdapter, EventConsumerPort)
        assert issubclass(HttpxHttpClientAdapter, HttpClientPort)
        assert issubclass(AnyioSandboxedToolRunnerAdapter, SandboxedToolRunnerPort)
        assert hasattr(AnyioStreamGuardrailFilterAdapter, "filter_stream")

    def test_httpx_client_timeout_resilience_default(self) -> None:
        client = HttpxHttpClientAdapter(timeout=45.0)
        assert client.default_timeout == 45.0

        default_client = HttpxHttpClientAdapter()
        assert default_client.default_timeout == 30.0
