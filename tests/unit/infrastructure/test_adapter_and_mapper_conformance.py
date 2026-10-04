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
    AnyioStreamGuardrailFilter,
    AnyioStreamGuardrailFilterAdapter,
)
from src.infrastructure.messaging.in_memory.in_memory_message_broker import (
    InMemoryMessageBroker,
    InMemoryMessageBrokerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_consumer_adapter import (
    RabbitMQConsumerAdapter,
    RabbitMqConsumerAdapter,
    RabbitMqEventConsumerAdapter,
)
from src.infrastructure.messaging.rabbitmq.rabbitmq_publisher_adapter import (
    RabbitMqEventPublisherAdapter,
    RabbitMQPublisherAdapter,
    RabbitMqPublisherAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_audit_repository import (
    InMemoryAuditRepository,
    InMemoryAuditRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_idempotency_repository import (
    InMemoryIdempotencyRepository,
    InMemoryIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_incident_repository import (
    InMemoryIncidentRepository,
    InMemoryIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_stream_buffer_repository import (
    InMemoryStreamBufferRepository,
    InMemoryStreamBufferRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.in_memory_tool_approval_repository import (
    InMemoryToolApprovalRepository,
    InMemoryToolApprovalRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.knowledge_repository import (
    InMemoryKnowledgeRepository,
    InMemoryKnowledgeRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.repository import (
    InMemoryConversationRepository,
    InMemoryConversationRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.tenant_repository import (
    InMemoryTenantRepository,
    InMemoryTenantRepositoryAdapter,
)
from src.infrastructure.persistence.in_memory.unit_of_work import (
    InMemoryUnitOfWork,
    InMemoryUnitOfWorkAdapter,
)
from src.infrastructure.persistence.mssql.audit_repository import (
    MssqlAuditRepository,
    MssqlAuditRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.governance_mapper import (
    GovernanceDataMapper,
    GovernanceMapper,
)
from src.infrastructure.persistence.mssql.idempotency_repository import (
    MssqlIdempotencyRepository,
    MssqlIdempotencyRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.knowledge_mapper import (
    KnowledgeDataMapper,
    KnowledgeMapper,
)
from src.infrastructure.persistence.mssql.mapper import (
    ConversationDataMapper,
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
    MssqlIncidentRepository,
    MssqlIncidentRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_knowledge_repository import (
    MssqlKnowledgeRepository,
    MssqlKnowledgeRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_tool_approval_repository import (
    MssqlToolApprovalRepository,
    MssqlToolApprovalRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.mssql_workflow_checkpoint_repository import (
    MssqlWorkflowCheckpointRepository,
    MssqlWorkflowCheckpointRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.outbox_repository import (
    MssqlOutboxRepository,
    MssqlOutboxRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.repository import (
    MssqlConversationRepository,
    MssqlConversationRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.stream_buffer_repository import (
    MssqlStreamBufferRepository,
    MssqlStreamBufferRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.tenant_mapper import (
    TenantDataMapper,
    TenantMapper,
)
from src.infrastructure.persistence.mssql.tenant_repository import (
    MssqlTenantRepository,
    MssqlTenantRepositoryAdapter,
)
from src.infrastructure.persistence.mssql.tool_approval_mapper import (
    ToolApprovalDataMapper,
    ToolApprovalMapper,
)
from src.infrastructure.persistence.mssql.unit_of_work import (
    MssqlUnitOfWork,
    MssqlUnitOfWorkAdapter,
)
from src.infrastructure.persistence.mssql.workflow_mapper import (
    WorkflowDataMapper,
    WorkflowMapper,
)
from src.infrastructure.shared.http_client.httpx_client import (
    HttpxClient,
    HttpxClientAdapter,
    HttpxHttpClientAdapter,
)
from src.infrastructure.shared.persistence.outbox.dispatcher import (
    OutboxDispatcher,
    OutboxDispatcherAdapter,
)
from src.infrastructure.shared.persistence.outbox.in_memory import (
    InMemoryOutboxRepository,
    InMemoryOutboxRepositoryAdapter,
)
from src.infrastructure.tools.anyio_sandboxed_tool_runner import (
    AnyioSandboxedToolRunner,
    AnyioSandboxedToolRunnerAdapter,
)


class TestMapperConformance:
    """Verifies that all mappers expose standard to_domain and to_persistence methods."""

    def test_should_expose_to_domain_and_to_persistence_on_conversation_mapper(self) -> None:
        assert hasattr(ConversationMapper, "to_domain") and callable(ConversationMapper.to_domain)
        assert hasattr(ConversationMapper, "to_persistence") and callable(
            ConversationMapper.to_persistence
        )
        assert ConversationMapper is ConversationDataMapper

        conv = Conversation.create("Test Conversation")
        model = ConversationMapper.to_persistence(conv)
        assert isinstance(model, ConversationModel)
        reconstituted = ConversationMapper.to_domain(model)
        assert reconstituted.id == conv.id
        assert reconstituted.title == conv.title

    def test_should_expose_to_domain_and_to_persistence_on_tenant_mapper(self) -> None:
        assert hasattr(TenantMapper, "to_domain") and callable(TenantMapper.to_domain)
        assert hasattr(TenantMapper, "to_persistence") and callable(TenantMapper.to_persistence)
        assert TenantMapper is TenantDataMapper

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
        assert KnowledgeMapper is KnowledgeDataMapper

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
        assert ToolApprovalMapper is ToolApprovalDataMapper

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
        assert GovernanceMapper is GovernanceDataMapper

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
        assert WorkflowMapper is WorkflowDataMapper


class TestAdapterNamingAndPortConformance:
    """Verifies that canonical <Technology><Port>Adapter aliases match and satisfy ports."""

    def test_mssql_adapter_aliases_match_canonical_classes(self) -> None:
        assert MssqlConversationRepositoryAdapter is MssqlConversationRepository
        assert issubclass(MssqlConversationRepository, ConversationRepositoryPort)

        assert MssqlTenantRepositoryAdapter is MssqlTenantRepository
        assert issubclass(MssqlTenantRepository, TenantRepositoryPort)

        assert MssqlIncidentRepositoryAdapter is MssqlIncidentRepository
        assert issubclass(MssqlIncidentRepository, IncidentRepositoryPort)

        assert MssqlKnowledgeRepositoryAdapter is MssqlKnowledgeRepository
        assert issubclass(MssqlKnowledgeRepository, KnowledgeRepositoryPort)

        assert MssqlToolApprovalRepositoryAdapter is MssqlToolApprovalRepository
        assert issubclass(MssqlToolApprovalRepository, ToolApprovalRepositoryPort)

        assert MssqlWorkflowCheckpointRepositoryAdapter is MssqlWorkflowCheckpointRepository

        assert MssqlAuditRepositoryAdapter is MssqlAuditRepository
        assert issubclass(MssqlAuditRepository, AuditRepositoryPort)

        assert MssqlIdempotencyRepositoryAdapter is MssqlIdempotencyRepository
        assert issubclass(MssqlIdempotencyRepository, IdempotencyRepositoryPort)

        assert MssqlOutboxRepositoryAdapter is MssqlOutboxRepository
        assert MssqlStreamBufferRepositoryAdapter is MssqlStreamBufferRepository
        assert issubclass(MssqlStreamBufferRepository, StreamBufferRepositoryPort)

        assert MssqlUnitOfWorkAdapter is MssqlUnitOfWork
        assert issubclass(MssqlUnitOfWork, UnitOfWorkPort)

    def test_in_memory_adapter_aliases_match_canonical_classes(self) -> None:
        assert InMemoryConversationRepositoryAdapter is InMemoryConversationRepository
        assert issubclass(InMemoryConversationRepository, ConversationRepositoryPort)

        assert InMemoryTenantRepositoryAdapter is InMemoryTenantRepository
        assert issubclass(InMemoryTenantRepository, TenantRepositoryPort)

        assert InMemoryIncidentRepositoryAdapter is InMemoryIncidentRepository
        assert issubclass(InMemoryIncidentRepository, IncidentRepositoryPort)

        assert InMemoryKnowledgeRepositoryAdapter is InMemoryKnowledgeRepository
        assert issubclass(InMemoryKnowledgeRepository, KnowledgeRepositoryPort)

        assert InMemoryToolApprovalRepositoryAdapter is InMemoryToolApprovalRepository
        assert issubclass(InMemoryToolApprovalRepository, ToolApprovalRepositoryPort)

        assert InMemoryAuditRepositoryAdapter is InMemoryAuditRepository
        assert issubclass(InMemoryAuditRepository, AuditRepositoryPort)

        assert InMemoryIdempotencyRepositoryAdapter is InMemoryIdempotencyRepository
        assert issubclass(InMemoryIdempotencyRepository, IdempotencyRepositoryPort)

        assert InMemoryStreamBufferRepositoryAdapter is InMemoryStreamBufferRepository
        assert issubclass(InMemoryStreamBufferRepository, StreamBufferRepositoryPort)

        assert InMemoryUnitOfWorkAdapter is InMemoryUnitOfWork
        assert issubclass(InMemoryUnitOfWork, UnitOfWorkPort)

        assert InMemoryMessageBrokerAdapter is InMemoryMessageBroker
        assert issubclass(InMemoryMessageBroker, MessageBrokerPort)
        assert issubclass(InMemoryMessageBroker, EventConsumerPort)

        assert InMemoryOutboxRepositoryAdapter is InMemoryOutboxRepository
        assert OutboxDispatcherAdapter is OutboxDispatcher

    def test_messaging_and_tools_adapter_aliases(self) -> None:
        assert RabbitMqPublisherAdapter is RabbitMQPublisherAdapter
        assert RabbitMqEventPublisherAdapter is RabbitMQPublisherAdapter
        assert issubclass(RabbitMQPublisherAdapter, MessageBrokerPort)

        assert RabbitMqConsumerAdapter is RabbitMQConsumerAdapter
        assert RabbitMqEventConsumerAdapter is RabbitMQConsumerAdapter
        assert issubclass(RabbitMQConsumerAdapter, EventConsumerPort)

        assert HttpxHttpClientAdapter is HttpxClient
        assert HttpxClientAdapter is HttpxClient
        assert issubclass(HttpxClient, HttpClientPort)

        assert AnyioSandboxedToolRunnerAdapter is AnyioSandboxedToolRunner
        assert issubclass(AnyioSandboxedToolRunner, SandboxedToolRunnerPort)

        assert AnyioStreamGuardrailFilterAdapter is AnyioStreamGuardrailFilter

    def test_httpx_client_timeout_resilience_default(self) -> None:
        client = HttpxClient(timeout=45.0)
        assert client.default_timeout == 45.0

        default_client = HttpxClient()
        assert default_client.default_timeout == 30.0
