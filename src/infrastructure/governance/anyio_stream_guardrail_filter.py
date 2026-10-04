"""AnyIO stream guardrail filter for real-time output token evaluation."""

from collections.abc import AsyncIterator

from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.domain.governance.ports.safety_guardrail_port import SafetyGuardrailPort
from src.domain.tenants.value_objects.tenant_id import TenantId


class AnyioStreamGuardrailFilterAdapter:
    """Filters outgoing stream tokens through safety guardrails in real time."""

    def __init__(
        self,
        guardrail: SafetyGuardrailPort,
        window_size: int = 500,
        tenant_id: TenantId | None = None,
    ) -> None:
        self._guardrail = guardrail
        self._window_size = window_size
        self._tenant_id = tenant_id

    async def filter_stream(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """Intercepts tokens from an async stream, raising SafetyPolicyViolationError on breach."""
        accumulated_text = ""

        async for chunk in stream:
            # Check current chunk against safety guardrails using sliding context
            verdict = await self._guardrail.evaluate_output_chunk(
                chunk=chunk,
                accumulated_text=accumulated_text[-self._window_size :],
                tenant_id=self._tenant_id,
            )

            if not verdict.is_safe:
                raise SafetyPolicyViolationError(
                    message=f"Output streaming blocked by guardrail: {verdict.violation_type}",
                    violation_type=verdict.violation_type or "OUTPUT_VIOLATION",
                    risk_score=verdict.risk_score,
                    matched_rule=verdict.matched_rule,
                )

            accumulated_text += chunk
            yield chunk


__all__ = ["AnyioStreamGuardrailFilterAdapter"]
