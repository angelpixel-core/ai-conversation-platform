"""Domain exceptions for tools, execution, and approvals."""

from src.domain.shared.domain_error import DomainError


class ToolNotFoundError(DomainError):
    """Raised when a requested tool is not found in the registry."""

    pass


class ToolExecutionError(DomainError):
    """Raised when a sandboxed tool execution fails critically."""

    pass


class InvalidApprovalStateError(DomainError, ValueError):
    """Raised when an approval request transition is invalid."""

    pass
