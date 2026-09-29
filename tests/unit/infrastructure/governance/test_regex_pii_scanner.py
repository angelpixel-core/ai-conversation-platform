"""Unit tests for RegexPiiScannerAdapter."""

import pytest

from src.domain.governance.ports.pii_scanner_port import PiiScannerPort
from src.infrastructure.governance.regex_pii_scanner_adapter import (
    RegexPiiScannerAdapter,
)


@pytest.fixture
def scanner() -> RegexPiiScannerAdapter:
    return RegexPiiScannerAdapter()


def test_scanner_implements_port(scanner: RegexPiiScannerAdapter) -> None:
    assert isinstance(scanner, PiiScannerPort)


def test_scan_and_mask_email(scanner: RegexPiiScannerAdapter) -> None:
    text = "Please reach out to support@acme-corp.com or john.doe@example.org for help."
    masked, matches = scanner.scan_and_mask_pii(text)

    assert "support@acme-corp.com" not in masked
    assert "john.doe@example.org" not in masked
    assert "[REDACTED_EMAIL]" in masked
    assert len(matches) == 2
    assert all(m.entity_type == "EMAIL" for m in matches)


def test_scan_and_mask_valid_credit_card_luhn(scanner: RegexPiiScannerAdapter) -> None:
    # Valid Visa card passes Luhn algorithm
    valid_card = "4532-0150-1234-5678"  # standard Luhn valid test number
    text = f"Payment details: card {valid_card} and expiration 12/28."
    masked, matches = scanner.scan_and_mask_pii(text)

    assert valid_card not in masked
    assert "[REDACTED_CREDIT_CARD]" in masked
    assert len(matches) == 1
    assert matches[0].entity_type == "CREDIT_CARD"


def test_scanner_ignores_invalid_credit_card_luhn(scanner: RegexPiiScannerAdapter) -> None:
    # 16-digit sequence that fails Luhn check
    invalid_card = "4532-0150-1234-5679"
    text = f"Order sequence id is {invalid_card}."
    masked, matches = scanner.scan_and_mask_pii(text)

    assert masked == text
    assert len(matches) == 0


def test_scan_and_mask_ssn_and_phone(scanner: RegexPiiScannerAdapter) -> None:
    text = "SSN: 123-45-6789 and mobile phone: +1-555-234-5678."
    masked, matches = scanner.scan_and_mask_pii(text)

    assert "123-45-6789" not in masked
    assert "+1-555-234-5678" not in masked
    assert "[REDACTED_SSN]" in masked
    assert "[REDACTED_PHONE]" in masked
    assert len(matches) == 2


def test_scan_and_mask_api_key(scanner: RegexPiiScannerAdapter) -> None:
    text = "API Key: sk-proj-1234567890abcdef1234567890abcdef12"
    masked, matches = scanner.scan_and_mask_pii(text)

    assert "sk-proj-" not in masked
    assert "[REDACTED_API_KEY]" in masked
    assert len(matches) == 1
    assert matches[0].entity_type == "API_KEY"


def test_scan_clean_text_returns_unmodified(scanner: RegexPiiScannerAdapter) -> None:
    text = "Hello world! This is a completely benign sentence about nature."
    masked, matches = scanner.scan_and_mask_pii(text)

    assert masked == text
    assert matches == []
