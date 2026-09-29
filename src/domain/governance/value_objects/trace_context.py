"""TraceContext Value Object adhering to W3C TraceContext standards."""

import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class TraceContext:
    """Immutable representation of distributed W3C Trace Context."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    trace_flags: int = 1
    tracestate: str | None = None

    def __post_init__(self) -> None:
        clean_trace = self.trace_id.strip().lower()
        if len(clean_trace) != 32:
            raise ValueError("trace_id debe contener exactamente 32 dígitos hexadecimales.")
        try:
            int(clean_trace, 16)
        except ValueError as err:
            raise ValueError("trace_id debe ser una cadena hexadecimal válida.") from err

        clean_span = self.span_id.strip().lower()
        if len(clean_span) != 16:
            raise ValueError("span_id debe contener exactamente 16 dígitos hexadecimales.")
        try:
            int(clean_span, 16)
        except ValueError as err:
            raise ValueError("span_id debe ser una cadena hexadecimal válida.") from err

        if self.parent_span_id is not None:
            clean_parent = self.parent_span_id.strip().lower()
            if len(clean_parent) != 16:
                raise ValueError(
                    "parent_span_id debe contener exactamente 16 dígitos hexadecimales."
                )
            try:
                int(clean_parent, 16)
            except ValueError as err:
                raise ValueError("parent_span_id debe ser una cadena hexadecimal válida.") from err

    @property
    def is_sampled(self) -> bool:
        """Indicates whether this trace is flagged for sampling and export."""
        return (self.trace_flags & 1) == 1

    def to_traceparent(self) -> str:
        """Serializes the context into standard W3C 'traceparent' header format."""
        return f"00-{self.trace_id.lower()}-{self.span_id.lower()}-{self.trace_flags:02x}"

    @classmethod
    def create_root(cls, sampled: bool = True) -> "TraceContext":
        """Generates a new root trace context with fresh trace and span identifiers."""
        trace_id = secrets.token_hex(16)
        span_id = secrets.token_hex(8)
        flags = 1 if sampled else 0
        return cls(trace_id=trace_id, span_id=span_id, parent_span_id=None, trace_flags=flags)

    @classmethod
    def from_traceparent(cls, header: str, tracestate: str | None = None) -> "TraceContext":
        """Parses a W3C traceparent header string."""
        parts = header.strip().split("-")
        if len(parts) != 4:
            raise ValueError("Formato traceparent inválido. Se requieren 4 segmentos.")

        version, trace_id, span_id, flags_hex = parts
        if version != "00" or len(version) != 2:
            raise ValueError("Versión de traceparent no soportada o inválida.")

        if len(trace_id) != 32:
            raise ValueError("trace_id inválido en traceparent: debe tener 32 caracteres.")
        try:
            int(trace_id, 16)
        except ValueError as err:
            raise ValueError("trace_id inválido en traceparent: no es hexadecimal.") from err

        if len(span_id) != 16:
            raise ValueError("span_id inválido en traceparent: debe tener 16 caracteres.")
        try:
            int(span_id, 16)
        except ValueError as err:
            raise ValueError("span_id inválido en traceparent: no es hexadecimal.") from err

        try:
            flags = int(flags_hex, 16)
        except ValueError as err:
            raise ValueError("trace_flags inválido en traceparent.") from err

        return cls(
            trace_id=trace_id.lower(),
            span_id=span_id.lower(),
            parent_span_id=None,
            trace_flags=flags,
            tracestate=tracestate,
        )

    def create_child_span(self) -> "TraceContext":
        """Spawns a child span inheriting trace_id, flags and tracestate."""
        child_span_id = secrets.token_hex(8)
        return TraceContext(
            trace_id=self.trace_id,
            span_id=child_span_id,
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
            tracestate=self.tracestate,
        )
