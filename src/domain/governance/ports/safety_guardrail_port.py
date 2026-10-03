"""SafetyGuardrailPort Driven Port."""

from abc import ABC, abstractmethod

from src.domain.governance.value_objects.safety_verdict import SafetyVerdict
from src.domain.tenants.value_objects.tenant_id import TenantId


class SafetyGuardrailPort(ABC):
    """Port for evaluating inputs and streaming output chunks against safety policies."""

    @abstractmethod
    async def evaluate_input(self, text: str, tenant_id: TenantId | None = None) -> SafetyVerdict:
        """Evaluates incoming user prompt against prompt injection and policy rules."""
        pass

    @abstractmethod
    async def evaluate_output_chunk(
        self, chunk: str, accumulated_text: str, tenant_id: TenantId | None = None
    ) -> SafetyVerdict:
        """Evaluates an outgoing stream chunk in real time against safety policies."""
        pass
