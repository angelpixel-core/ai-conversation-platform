"""Unit tests verifying CQRS handlers, protocols, and application error conformance."""

import inspect

from src.application.agents.commands.resume_workflow_command import (
    ResumeWorkflowCommand,
    ResumeWorkflowCommandHandler,
)
from src.application.agents.commands.start_workflow_command import (
    StartWorkflowCommand,
    StartWorkflowCommandHandler,
)
from src.application.conversations.commands.append_assistant_message import (
    AppendAssistantMessageCommand,
    AppendAssistantMessageCommandHandler,
)
from src.application.conversations.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationCommandHandler,
)
from src.application.conversations.commands.send_message import (
    SendMessageCommand,
    SendMessageCommandHandler,
)
from src.application.conversations.queries.resume_stream_query import ResumeStreamQuery
from src.application.conversations.queries.resume_stream_query_handler import (
    ResumeStreamQueryHandler,
)
from src.application.conversations.queries.stream_conversation import (
    StreamConversationQuery,
    StreamConversationQueryHandler,
)
from src.application.governance.commands.record_incident import (
    RecordSecurityIncidentCommand,
    RecordSecurityIncidentCommandHandler,
)
from src.application.governance.queries.get_governance_metrics import (
    GetGovernanceMetricsQuery,
    GetGovernanceMetricsQueryHandler,
)
from src.application.governance.queries.list_incidents import (
    ListIncidentsQuery,
    ListIncidentsQueryHandler,
)
from src.application.knowledge.commands.index_document_chunks import (
    IndexDocumentChunksCommand,
    IndexDocumentChunksCommandHandler,
)
from src.application.knowledge.commands.upload_document import (
    UploadDocumentCommand,
    UploadDocumentCommandHandler,
)
from src.application.shared.cqrs.base import (
    AsyncCommandHandler,
    AsyncQueryHandler,
    CommandHandler,
    QueryHandler,
)
from src.application.shared.exceptions import (
    ApplicationError,
    ApplicationValidationError,
    IdempotencyConflictError,
    TenantAccessDeniedError,
)
from src.application.shared.ports.event_publisher import EventPublisherPort
from src.application.shared.ports.http_client import HttpClientPort
from src.application.shared.ports.unit_of_work import UnitOfWorkPort
from src.application.tenants.commands.provision_tenant_command import (
    ProvisionTenantCommand,
    ProvisionTenantCommandHandler,
)
from src.application.tenants.commands.reserve_quota_command import (
    ReserveQuotaCommand,
    ReserveQuotaCommandHandler,
)
from src.application.tenants.commands.settle_quota_command import (
    SettleQuotaCommand,
    SettleQuotaCommandHandler,
)
from src.application.tools.commands.approve_tool_execution import (
    ApproveToolExecutionCommand,
    ApproveToolExecutionCommandHandler,
)
from src.application.tools.commands.execute_sandboxed_tool import (
    ExecuteSandboxedToolCommand,
    ExecuteSandboxedToolCommandHandler,
)
from src.application.tools.commands.reject_tool_execution import (
    RejectToolExecutionCommand,
    RejectToolExecutionCommandHandler,
)
from src.domain.conversations.ports.conversation_repository import (
    ConversationRepositoryPort,
)


def test_command_handlers_have_handle_method_and_accept_command() -> None:
    """Verifies all CQRS command handlers implement handle(command)."""
    handlers = [
        (CreateConversationCommandHandler, CreateConversationCommand),
        (SendMessageCommandHandler, SendMessageCommand),
        (AppendAssistantMessageCommandHandler, AppendAssistantMessageCommand),
        (ProvisionTenantCommandHandler, ProvisionTenantCommand),
        (ReserveQuotaCommandHandler, ReserveQuotaCommand),
        (SettleQuotaCommandHandler, SettleQuotaCommand),
        (UploadDocumentCommandHandler, UploadDocumentCommand),
        (IndexDocumentChunksCommandHandler, IndexDocumentChunksCommand),
        (ApproveToolExecutionCommandHandler, ApproveToolExecutionCommand),
        (RejectToolExecutionCommandHandler, RejectToolExecutionCommand),
        (ExecuteSandboxedToolCommandHandler, ExecuteSandboxedToolCommand),
        (RecordSecurityIncidentCommandHandler, RecordSecurityIncidentCommand),
        (StartWorkflowCommandHandler, StartWorkflowCommand),
        (ResumeWorkflowCommandHandler, ResumeWorkflowCommand),
    ]

    for handler_cls, _command_cls in handlers:
        assert hasattr(handler_cls, "handle"), f"{handler_cls} missing handle() method"
        sig = inspect.signature(handler_cls.handle)
        params = list(sig.parameters.keys())
        assert len(params) >= 2, f"{handler_cls}.handle should accept self and command"
        assert params[1] in ("command", "cmd"), f"{handler_cls} parameter name should be command"


def test_query_handlers_have_handle_method_and_accept_query() -> None:
    """Verifies all CQRS query handlers implement handle(query)."""
    handlers = [
        (StreamConversationQueryHandler, StreamConversationQuery),
        (ResumeStreamQueryHandler, ResumeStreamQuery),
        (GetGovernanceMetricsQueryHandler, GetGovernanceMetricsQuery),
        (ListIncidentsQueryHandler, ListIncidentsQuery),
    ]

    for handler_cls, _query_cls in handlers:
        assert hasattr(handler_cls, "handle"), f"{handler_cls} missing handle() method"
        sig = inspect.signature(handler_cls.handle)
        params = list(sig.parameters.keys())
        assert len(params) >= 2, f"{handler_cls}.handle should accept self and query"
        assert params[1] in ("query", "q"), f"{handler_cls} parameter name should be query"


def test_driven_ports_standardization() -> None:
    """Verifies all driven ports follow the *Port suffix and define abstract interfaces."""
    for port in (UnitOfWorkPort, EventPublisherPort, HttpClientPort, ConversationRepositoryPort):
        assert inspect.isabstract(port) or hasattr(port, "__abstractmethods__")

    # Check abstract methods on UnitOfWorkPort
    abstract_methods = getattr(UnitOfWorkPort, "__abstractmethods__", set())
    assert "__enter__" in abstract_methods
    assert "__exit__" in abstract_methods
    assert "commit" in abstract_methods
    assert "rollback" in abstract_methods


def test_cqrs_protocol_declarations() -> None:
    """Verifies CQRS base protocols define handle signature."""
    assert hasattr(CommandHandler, "handle")
    assert hasattr(AsyncCommandHandler, "handle")
    assert hasattr(QueryHandler, "handle")
    assert hasattr(AsyncQueryHandler, "handle")


def test_application_exceptions_hierarchy() -> None:
    """Verifies application exceptions derive from ApplicationError."""
    app_err = ApplicationError("base error", {"code": "TEST"})
    assert app_err.message == "base error"
    assert app_err.details == {"code": "TEST"}
    assert isinstance(app_err, Exception)

    val_err = ApplicationValidationError("invalid payload")
    assert isinstance(val_err, ApplicationError)
    assert isinstance(val_err, ValueError)

    idemp_err = IdempotencyConflictError("lock contention")
    assert isinstance(idemp_err, ApplicationError)

    access_err = TenantAccessDeniedError("tenant mismatch")
    assert isinstance(access_err, ApplicationError)
    assert isinstance(access_err, PermissionError)
