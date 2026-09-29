"""Domain exceptions for Multi-Agent Workflows and State Graphs."""

from src.domain.shared.domain_error import DomainError


class WorkflowNotFoundError(DomainError):
    """Raised when a requested workflow instance is not found."""

    pass


class InvalidGraphTransitionError(DomainError):
    """Raised when a state transition or graph edge is invalid."""

    pass


class GraphCycleDetectedError(DomainError):
    """Raised when a cycle is detected in a Directed Acyclic Graph."""

    pass


class SubAgentExecutionError(DomainError):
    """Raised when a subagent fails execution critically."""

    pass


class WorkflowStateError(DomainError):
    """Raised when an operation is attempted in an incompatible workflow state."""

    pass
