"""Canonical template: ToolResult Value Object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolResult:
    """Immutable outcome of a sandboxed tool execution."""

    call_id: str
    output: str
    is_error: bool = False
    execution_time_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("El call_id no puede estar vacío.")
        if self.execution_time_ms < 0:
            raise ValueError("El execution_time_ms no puede ser negativo.")
