"""SafetyGuardrailPipelineService application service.

Coordinates safety evaluation and PII detection concurrently using AnyIO structured concurrency.
"""

from dataclasses import dataclass, field

import anyio

from src.domain.governance.ports.pii_scanner_port import PiiScannerPort
from src.domain.governance.ports.safety_guardrail_port import SafetyGuardrailPort
from src.domain.governance.value_objects.pii_entity_match import PiiEntityMatch
from src.domain.governance.value_objects.safety_verdict import SafetyVerdict
from src.domain.tenants.value_objects.tenant_id import TenantId


@dataclass(frozen=True)
class GuardrailPipelineResult:
    """Aggregated output of guardrail evaluation and PII scanning."""

    sanitized_text: str
    verdict: SafetyVerdict
    pii_matches: list[PiiEntityMatch] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """Indicates whether content passed all safety checks."""
        return self.verdict.is_safe

    @property
    def has_pii(self) -> bool:
        """Indicates whether sensitive PII was detected and redacted."""
        return len(self.pii_matches) > 0


class SafetyGuardrailPipelineService:
    """Application pipeline orchestrating concurrent safety and PII guardrails."""

    def __init__(
        self,
        safety_guardrail: SafetyGuardrailPort,
        pii_scanner: PiiScannerPort,
    ) -> None:
        self._safety_guardrail = safety_guardrail
        self._pii_scanner = pii_scanner

    async def evaluate_and_sanitize(
        self, text: str, tenant_id: TenantId | None = None
    ) -> GuardrailPipelineResult:
        """Evaluates input text against safety policies and redacts PII concurrently."""
        verdict: SafetyVerdict = SafetyVerdict.safe()
        masked_text: str = text
        pii_matches: list[PiiEntityMatch] = []

        async def _check_safety() -> None:
            nonlocal verdict
            verdict = await self._safety_guardrail.evaluate_input(text, tenant_id)

        def _check_pii() -> None:
            nonlocal masked_text, pii_matches
            masked_text, pii_matches = self._pii_scanner.scan_and_mask_pii(text)

        async with anyio.create_task_group() as tg:
            tg.start_soon(_check_safety)
            _check_pii()

        return GuardrailPipelineResult(
            sanitized_text=masked_text,
            verdict=verdict,
            pii_matches=pii_matches,
        )

    async def evaluate_stream_chunk(
        self, chunk: str, accumulated_text: str, tenant_id: TenantId | None = None
    ) -> SafetyVerdict:
        """Evaluates an outgoing stream chunk in real time against safety policies."""
        return await self._safety_guardrail.evaluate_output_chunk(
            chunk, accumulated_text, tenant_id
        )
