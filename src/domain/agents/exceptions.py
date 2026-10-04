"""Domain exceptions for Multi-Agent Workflows and State Graphs."""

from src.domain.shared.exceptions import DomainError, EntityNotFoundError


class WorkflowNotFoundError(EntityNotFoundError, ValueError):
    """Raised when a requested workflow instance is not found."""

    pass


class InvalidGraphTransitionError(DomainError, ValueError):
    """Raised when a state transition or graph edge is invalid."""

    pass


class GraphCycleDetectedError(DomainError, ValueError):
    """Raised when a cycle is detected in a Directed Acyclic Graph."""

    pass


class SubAgentExecutionError(DomainError, RuntimeError):
    """Raised when a subagent fails execution critically."""

    pass


class WorkflowStateError(DomainError, ValueError):
    """Raised when an operation is attempted in an incompatible workflow state."""

    pass
