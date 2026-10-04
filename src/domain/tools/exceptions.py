"""Domain exceptions for tools, execution, and approvals."""

from src.domain.shared.exceptions import DomainError, EntityNotFoundError


class ToolNotFoundError(EntityNotFoundError, ValueError):
    """Raised when a requested tool is not found in the registry."""

    pass


class ToolExecutionError(DomainError, RuntimeError):
    """Raised when a sandboxed tool execution fails critically."""

    pass


class InvalidApprovalStateError(DomainError, ValueError):
    """Raised when an approval request transition is invalid."""

    pass


class ToolApprovalNotFoundError(EntityNotFoundError, ValueError):
    """Raised when an approval request is not found for a tenant."""

    pass


class ToolNotAllowedError(DomainError, ValueError):
    """Raised when a tool is not permitted for execution in the current tenant policy."""

    pass
