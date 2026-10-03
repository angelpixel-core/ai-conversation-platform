"""Heuristic and regex-based prompt injection detector adapter."""

import re

from src.domain.governance.ports.safety_guardrail_port import SafetyGuardrailPort
from src.domain.governance.value_objects.safety_verdict import SafetyVerdict
from src.domain.tenants.value_objects.tenant_id import TenantId


class HeuristicInjectionDetectorAdapter(SafetyGuardrailPort):
    """High-speed heuristic injection and jailbreak detector (<5ms latency)."""

    _OVERRIDE_RE = re.compile(
        r"(?i)\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?"
        r"(?:previous|earlier|prior|above|system)\s+"
        r"(?:instructions|prompts|rules|commands|directives)\b"
    )
    _DAN_RE = re.compile(
        r"(?i)\b(?:DAN|jailbreak|developer\s+mode|unrestricted\s+ai|"
        r"bypass\s+(?:rules|filters|safeguards|ethical))\b"
    )
    _TAG_RE = re.compile(
        r"(?i)(?:</system>|</prompt>|\[SYSTEM\s+INSTRUCTION(?::|\])|\[ADMIN\]|<override>)"
    )
    _CRED_LEAK_RE = re.compile(r"\b(?:sk-proj-[a-zA-Z0-9_-]{10,}|AIza[0-9A-Za-z-_]{20,})\b")

    async def evaluate_input(self, text: str, tenant_id: TenantId | None = None) -> SafetyVerdict:
        """Evaluates input text against known prompt injection and jailbreak vectors."""
        # 1. Delimiter tag escaping
        if self._TAG_RE.search(text):
            return SafetyVerdict.violation(
                violation_type="TAG_INJECTION",
                risk_score=0.88,
                matched_rule="DELIMITER_ESCAPING",
                details={"reason": "Attempted delimiter tag escaping or prompt override injection"},
            )

        # 2. DAN / Developer Mode jailbreaks
        if self._DAN_RE.search(text):
            return SafetyVerdict.violation(
                violation_type="PROMPT_INJECTION",
                risk_score=0.95,
                matched_rule="DAN_JAILBREAK",
                details={"reason": "DAN or unconstrained developer mode persona detected"},
            )

        # 3. Instruction override attacks
        if self._OVERRIDE_RE.search(text):
            return SafetyVerdict.violation(
                violation_type="PROMPT_INJECTION",
                risk_score=0.90,
                matched_rule="INSTRUCTION_OVERRIDE",
                details={"reason": "System instruction disregard/override attempt"},
            )

        return SafetyVerdict.safe()

    async def evaluate_output_chunk(
        self, chunk: str, accumulated_text: str, tenant_id: TenantId | None = None
    ) -> SafetyVerdict:
        """Evaluates an outgoing stream chunk in real time against safety policies."""
        combined = accumulated_text[-200:] + chunk if accumulated_text else chunk
        if self._CRED_LEAK_RE.search(combined):
            return SafetyVerdict.violation(
                violation_type="OUTPUT_CREDENTIAL_LEAK",
                risk_score=0.99,
                matched_rule="OUTPUT_CREDENTIAL_LEAK_RULE",
                details={"reason": "Potential API credential leak in outgoing stream chunk"},
            )

        return SafetyVerdict.safe()
