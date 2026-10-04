"""Base application layer exceptions."""


class ApplicationError(Exception):
    """Base class for all application layer exceptions."""

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ApplicationValidationError(ApplicationError, ValueError):
    """Raised when an application-level input or command payload fails validation."""

    pass


class IdempotencyConflictError(ApplicationError):
    """Raised when an operation with the same idempotency key is already running or locked."""

    pass


class TenantAccessDeniedError(ApplicationError, PermissionError):
    """Raised when an operation is attempted across tenant boundaries without authorization."""

    pass
