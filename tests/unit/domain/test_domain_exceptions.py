"""Unit tests for unified domain exceptions hierarchy and dual-inheritance behavior."""

from src.domain.conversations.exceptions import (
    ConsecutiveAssistantMessageError,
    ConsecutiveUserMessageError,
    ConversationNotFoundError,
    InvalidConversationTitleError,
    MessageValidationError,
)
from src.domain.knowledge.exceptions import (
    DocumentNotFoundError,
    DocumentValidationError,
    InvalidDocumentChunkError,
)
from src.domain.shared.exceptions import (
    DomainError,
    DomainException,
    DomainValidationError,
    EntityNotFoundError,
    InvariantViolationError,
)
from src.domain.tenants.exceptions import (
    InsufficientBudgetError,
    InvalidBudgetOperationError,
    ModelNotAllowedError,
    TenantAlreadyExistsError,
    TenantNotFoundError,
    TenantSuspendedError,
    TenantValidationError,
)
from src.domain.tools.exceptions import (
    InvalidApprovalStateError,
    ToolExecutionError,
    ToolNotFoundError,
)


def test_domain_exception_alias() -> None:
    assert DomainException is DomainError
    err = DomainError("generic error")
    assert isinstance(err, DomainException)
    assert isinstance(err, Exception)


def test_domain_validation_error_dual_inheritance() -> None:
    err = DomainValidationError("invalid format")
    assert isinstance(err, DomainError)
    assert isinstance(err, ValueError)


def test_entity_not_found_error_inheritance() -> None:
    err = EntityNotFoundError("entity missing")
    assert isinstance(err, DomainError)


def test_invariant_violation_error_inheritance() -> None:
    err = InvariantViolationError("invariant violated")
    assert isinstance(err, DomainError)


def test_tenant_exceptions_dual_inheritance() -> None:
    # Validation and arithmetic errors inherit from ValueError for backward compatibility
    validation_err = TenantValidationError("invalid tenant slug")
    assert isinstance(validation_err, DomainError)
    assert isinstance(validation_err, ValueError)

    budget_op_err = InvalidBudgetOperationError("negative amount")
    assert isinstance(budget_op_err, DomainError)
    assert isinstance(budget_op_err, ValueError)

    insufficient_budget_err = InsufficientBudgetError("quota exceeded")
    assert isinstance(insufficient_budget_err, DomainError)
    assert isinstance(insufficient_budget_err, ValueError)

    suspended_err = TenantSuspendedError("tenant suspended")
    assert isinstance(suspended_err, DomainError)
    assert isinstance(suspended_err, ValueError)

    model_err = ModelNotAllowedError("model not allowed")
    assert isinstance(model_err, DomainError)
    assert isinstance(model_err, ValueError)

    # Entity existence errors
    not_found_err = TenantNotFoundError("tenant not found")
    assert isinstance(not_found_err, EntityNotFoundError)
    assert isinstance(not_found_err, DomainError)

    already_exists_err = TenantAlreadyExistsError("tenant exists")
    assert isinstance(already_exists_err, DomainError)


def test_conversation_exceptions_inheritance() -> None:
    not_found = ConversationNotFoundError("conv missing")
    assert isinstance(not_found, EntityNotFoundError)
    assert isinstance(not_found, DomainError)

    title_err = InvalidConversationTitleError("empty title")
    assert isinstance(title_err, DomainValidationError)
    assert isinstance(title_err, ValueError)
    assert isinstance(title_err, DomainError)

    consec_user = ConsecutiveUserMessageError("cannot append user message")
    assert isinstance(consec_user, DomainError)

    consec_asst = ConsecutiveAssistantMessageError("cannot append assistant message")
    assert isinstance(consec_asst, DomainError)

    msg_val = MessageValidationError("too long")
    assert isinstance(msg_val, DomainValidationError)
    assert isinstance(msg_val, ValueError)


def test_knowledge_exceptions_inheritance() -> None:
    doc_not_found = DocumentNotFoundError("doc missing")
    assert isinstance(doc_not_found, EntityNotFoundError)
    assert isinstance(doc_not_found, DomainError)

    doc_val = DocumentValidationError("empty filename")
    assert isinstance(doc_val, DomainValidationError)
    assert isinstance(doc_val, ValueError)

    chunk_err = InvalidDocumentChunkError("zero chunks")
    assert isinstance(chunk_err, DomainValidationError)
    assert isinstance(chunk_err, ValueError)


def test_tools_exceptions_inheritance() -> None:
    approval_state_err = InvalidApprovalStateError("cannot approve")
    assert isinstance(approval_state_err, DomainError)
    assert isinstance(approval_state_err, ValueError)

    tool_not_found = ToolNotFoundError("missing tool")
    assert isinstance(tool_not_found, DomainError)

    tool_exec_err = ToolExecutionError("sandbox crash")
    assert isinstance(tool_exec_err, DomainError)
