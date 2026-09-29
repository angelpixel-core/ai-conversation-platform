"""Unit tests for AnyioStreamGuardrailFilter."""

from collections.abc import AsyncIterator

import pytest

from src.domain.governance.exceptions import SafetyPolicyViolationError
from src.domain.governance.value_objects.safety_verdict import SafetyVerdict
from src.domain.tenants.value_objects.tenant_id import TenantId
from src.infrastructure.governance.anyio_stream_guardrail_filter import (
    AnyioStreamGuardrailFilter,
)


class DummySafetyGuardrail:
    """Mock guardrail port for testing stream filtering."""

    def __init__(self, block_on_text: str | None = None) -> None:
        self.block_on_text = block_on_text

    async def evaluate_input(self, text: str, tenant_id: TenantId | None = None) -> SafetyVerdict:
        return SafetyVerdict.safe()

    async def evaluate_output_chunk(
        self, chunk: str, accumulated_text: str, tenant_id: TenantId | None = None
    ) -> SafetyVerdict:
        if self.block_on_text and self.block_on_text in (accumulated_text + chunk):
            return SafetyVerdict.violation(
                violation_type="OUTPUT_LEAK",
                risk_score=0.99,
                matched_rule="FORBIDDEN_OUTPUT_RULE",
            )
        return SafetyVerdict.safe()


async def sample_generator(chunks: list[str]) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk


@pytest.mark.anyio
async def test_stream_filter_passes_safe_chunks() -> None:
    guardrail = DummySafetyGuardrail()
    stream_filter = AnyioStreamGuardrailFilter(guardrail=guardrail)

    chunks = ["Hello", " world", ", how", " are you?"]
    output = []
    async for chunk in stream_filter.filter_stream(sample_generator(chunks)):
        output.append(chunk)

    assert output == chunks


@pytest.mark.anyio
async def test_stream_filter_aborts_on_violation() -> None:
    guardrail = DummySafetyGuardrail(block_on_text="FORBIDDEN_TOKEN")
    stream_filter = AnyioStreamGuardrailFilter(guardrail=guardrail)

    chunks = ["Processing: ", "here is ", "FORBIDDEN_", "TOKEN_EXPLOIT"]

    output = []
    with pytest.raises(SafetyPolicyViolationError) as exc_info:
        async for chunk in stream_filter.filter_stream(sample_generator(chunks)):
            output.append(chunk)

    assert exc_info.value.violation_type == "OUTPUT_LEAK"
    assert exc_info.value.matched_rule == "FORBIDDEN_OUTPUT_RULE"
    assert output == ["Processing: ", "here is "]
