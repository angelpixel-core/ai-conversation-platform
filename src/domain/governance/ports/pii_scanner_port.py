"""PiiScannerPort Driven Port."""

from abc import ABC, abstractmethod

from src.domain.governance.value_objects.pii_entity_match import PiiEntityMatch


class PiiScannerPort(ABC):
    """Port for scanning text and masking personal identifiable information."""

    @abstractmethod
    def scan_and_mask_pii(self, text: str) -> tuple[str, list[PiiEntityMatch]]:
        """Scans input text for sensitive PII and returns masked text alongside matches."""
        pass
