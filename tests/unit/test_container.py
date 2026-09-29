"""Unit tests for Application Container composition root."""

from fastapi import FastAPI

from src.application.conversations.commands.create_conversation import (
    CreateConversationHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQueryHandler,
)
from src.application.conversations.services.stream_recovery_service import (
    StreamRecoveryService,
)
from src.application.governance.services.guardrail_pipeline_service import (
    SafetyGuardrailPipelineService,
)
from src.application.knowledge.services.hybrid_retriever_service import (
    HybridRetrieverService,
)
from src.application.routing.services.model_router_service import (
    ModelRouterService,
)
from src.application.shared.governance.guarded_command_executor import (
    GuardedCommandExecutor,
)
from src.application.shared.idempotency.idempotent_command_executor import (
    IdempotentCommandExecutor,
)

from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommandHandler,
)
from src.application.tenants.commands.settle_quota_command import (
    SettleQuotaCommandHandler,
)
from src.application.tools.services.tool_policy_evaluator_service import (
    ToolPolicyEvaluatorService,
)
from src.container import AppContainer, create_app_container
from src.domain.governance.ports.incident_repository_port import (
    IncidentRepositoryPort,
)
from src.domain.governance.ports.pii_scanner_port import PiiScannerPort
from src.domain.governance.ports.safety_guardrail_port import (
    SafetyGuardrailPort,
)
from src.domain.knowledge.ports.embedding_client_port import EmbeddingClientPort
from src.domain.routing.ports.model_catalog_port import ModelCatalogPort

from src.domain.tools.ports.sandboxed_tool_runner_port import (
    SandboxedToolRunnerPort,
)
from src.domain.tools.ports.tool_approval_repository_port import (
    ToolApprovalRepositoryPort,
)
from src.infrastructure.persistence.in_memory import (
    InMemoryAuditRepositoryAdapter,
    InMemoryIdempotencyRepositoryAdapter,
    InMemoryStreamBufferRepositoryAdapter,
    InMemoryUnitOfWork,
)
from src.infrastructure.persistence.mssql import (
    MssqlAuditRepository,
    MssqlIdempotencyRepository,
    MssqlStreamBufferRepository,
    MssqlUnitOfWork,
)
from src.infrastructure.routing.in_memory_model_catalog import (
    InMemoryModelCatalogAdapter,
)
from src.infrastructure.shared.config.settings import (
    PersistenceDriver,
    Settings,
)


def test_create_app_container_default_wires_in_memory() -> None:
    settings = Settings(PERSISTENCE_DRIVER=PersistenceDriver.IN_MEMORY)
    container = create_app_container(settings=settings)

    assert isinstance(container, AppContainer)
    assert isinstance(container.unit_of_work, InMemoryUnitOfWork)
    assert isinstance(container.idempotency_repo, InMemoryIdempotencyRepositoryAdapter)
    assert isinstance(container.audit_repo, InMemoryAuditRepositoryAdapter)
    assert isinstance(container.stream_buffer_repo, InMemoryStreamBufferRepositoryAdapter)
    assert isinstance(container.stream_recovery_service, StreamRecoveryService)
    assert isinstance(container.idempotent_executor, IdempotentCommandExecutor)
    assert isinstance(container.create_conversation_handler, CreateConversationHandler)
    assert isinstance(container.send_message_handler, SendMessageHandler)
    assert isinstance(container.stream_conversation_handler, StreamConversationQueryHandler)
    assert isinstance(container.fastapi_app, FastAPI)
    assert isinstance(container.model_catalog, ModelCatalogPort)
    assert isinstance(container.model_router_service, ModelRouterService)
    assert isinstance(container.reserve_quota_handler, ReserveQuotaCommandHandler)
    assert isinstance(container.settle_quota_handler, SettleQuotaCommandHandler)
    assert isinstance(container.retriever_service, HybridRetrieverService)
    assert isinstance(container.embedding_client, EmbeddingClientPort)
    assert isinstance(container.tool_approval_repo, ToolApprovalRepositoryPort)
    assert isinstance(container.tool_runner, SandboxedToolRunnerPort)
    assert isinstance(container.tool_policy_evaluator, ToolPolicyEvaluatorService)
    assert isinstance(container.incident_repo, IncidentRepositoryPort)
    assert isinstance(container.pii_scanner, PiiScannerPort)
    assert isinstance(container.safety_guardrail, SafetyGuardrailPort)
    assert isinstance(container.guardrail_pipeline, SafetyGuardrailPipelineService)
    assert isinstance(container.guarded_executor, GuardedCommandExecutor)


def test_create_app_container_with_mssql_driver() -> None:
    settings = Settings(
        PERSISTENCE_DRIVER=PersistenceDriver.MSSQL,
        DATABASE_URL="sqlite:///:memory:",
    )
    container = create_app_container(settings=settings)

    assert isinstance(container, AppContainer)
    assert isinstance(container.unit_of_work, MssqlUnitOfWork)
    assert isinstance(container.idempotency_repo, MssqlIdempotencyRepository)
    assert isinstance(container.audit_repo, MssqlAuditRepository)
    assert isinstance(container.stream_buffer_repo, MssqlStreamBufferRepository)
    assert isinstance(container.stream_recovery_service, StreamRecoveryService)
    assert isinstance(container.idempotent_executor, IdempotentCommandExecutor)
    assert isinstance(container.fastapi_app, FastAPI)
    assert isinstance(container.model_catalog, ModelCatalogPort)
    assert isinstance(container.model_router_service, ModelRouterService)
    assert isinstance(container.reserve_quota_handler, ReserveQuotaCommandHandler)
    assert isinstance(container.settle_quota_handler, SettleQuotaCommandHandler)
    assert isinstance(container.retriever_service, HybridRetrieverService)
    assert isinstance(container.embedding_client, EmbeddingClientPort)
    assert isinstance(container.incident_repo, IncidentRepositoryPort)



def test_create_app_container_with_custom_catalog_and_tenant_middleware() -> None:
    custom_catalog = InMemoryModelCatalogAdapter()
    container = create_app_container(
        model_catalog=custom_catalog,
        enable_tenant_middleware=True,
    )
    assert container.model_catalog is custom_catalog
    assert isinstance(container.fastapi_app, FastAPI)
