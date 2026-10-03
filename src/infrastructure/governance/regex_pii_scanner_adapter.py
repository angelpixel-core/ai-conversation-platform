"""Regex and Luhn algorithm-based high performance PII scanner adapter.

Adheres to Zero-Bloat Rule (<10ms execution, no heavy ML libraries).
"""

import re

from src.domain.governance.ports.pii_scanner_port import PiiScannerPort
from src.domain.governance.value_objects.pii_entity_match import PiiEntityMatch


def is_luhn_valid(number_str: str) -> bool:
    """Validates number sequence using the Luhn checksum formula."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class RegexPiiScannerAdapter(PiiScannerPort):
    """High-speed PII scanner using precompiled regexes and Luhn card validation."""

    # Precompiled regular expressions for sensitive entities
    _EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    _CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    _SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    _PHONE_RE = re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    _API_KEY_RE = re.compile(
        r"\b(?:sk-proj-[a-zA-Z0-9_-]{20,}|AIza[0-9A-Za-z-_]{35}|ghp_[0-9a-zA-Z]{36})\b"
    )

    def _find_raw_matches(self, text: str) -> list[tuple[int, int, str, str]]:
        matches: list[tuple[int, int, str, str]] = []
        for m in self._API_KEY_RE.finditer(text):
            matches.append((m.start(), m.end(), "API_KEY", "[REDACTED_API_KEY]"))
        for m in self._EMAIL_RE.finditer(text):
            matches.append((m.start(), m.end(), "EMAIL", "[REDACTED_EMAIL]"))
        for m in self._CARD_RE.finditer(text):
            if is_luhn_valid(m.group()):
                matches.append((m.start(), m.end(), "CREDIT_CARD", "[REDACTED_CREDIT_CARD]"))
        for m in self._SSN_RE.finditer(text):
            matches.append((m.start(), m.end(), "SSN", "[REDACTED_SSN]"))
        for m in self._PHONE_RE.finditer(text):
            matches.append((m.start(), m.end(), "PHONE", "[REDACTED_PHONE]"))
        return matches

    def _filter_overlapping(
        self, matches: list[tuple[int, int, str, str]]
    ) -> list[tuple[int, int, str, str]]:
        matches.sort(key=lambda x: (x[0], -x[1]))
        non_overlapping: list[tuple[int, int, str, str]] = []
        last_end = -1
        for start, end, entity_type, placeholder in matches:
            if start >= last_end:
                non_overlapping.append((start, end, entity_type, placeholder))
                last_end = end
        return non_overlapping

    def scan_and_mask_pii(self, text: str) -> tuple[str, list[PiiEntityMatch]]:
        """Scans raw text and returns sanitized text with audit metadata."""
        matches = self._find_raw_matches(text)
        if not matches:
            return text, []

        non_overlapping = self._filter_overlapping(matches)
        entity_matches: list[PiiEntityMatch] = []
        result_parts: list[str] = []
        curr_idx = 0

        for start, end, entity_type, placeholder in non_overlapping:
            result_parts.append(text[curr_idx:start])
            result_parts.append(placeholder)
            curr_idx = end

            entity_matches.append(
                PiiEntityMatch(
                    entity_type=entity_type,
                    start_idx=start,
                    end_idx=end,
                    masked_value=placeholder,
                    original_preview=text[start:end],
                )
            )

        result_parts.append(text[curr_idx:])
        return "".join(result_parts), entity_matches
