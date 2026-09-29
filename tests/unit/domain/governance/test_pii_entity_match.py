"""Unit tests for PiiEntityMatch Value Object."""

from dataclasses import FrozenInstanceError

import pytest
from src.domain.governance.value_objects.pii_entity_match import PiiEntityMatch


def test_pii_entity_match_creation() -> None:
    match = PiiEntityMatch(
        entity_type="CREDIT_CARD",
        start_idx=10,
        end_idx=26,
        masked_value="[REDACTED_CREDIT_CARD]",
        original_preview="4532********9810",
    )
    assert match.entity_type == "CREDIT_CARD"
    assert match.start_idx == 10
    assert match.end_idx == 26
    assert match.masked_value == "[REDACTED_CREDIT_CARD]"
    assert match.original_preview == "4532********9810"
    assert match.span == (10, 26)


def test_pii_entity_match_immutability() -> None:
    match = PiiEntityMatch(
        entity_type="EMAIL",
        start_idx=0,
        end_idx=15,
        masked_value="[REDACTED_EMAIL]",
        original_preview="j***@example.com",
    )
    with pytest.raises(FrozenInstanceError):
        match.start_idx = 5  # type: ignore[misc]


def test_pii_entity_match_invalid_indices() -> None:
    with pytest.raises(ValueError, match="El start_idx debe ser mayor o igual a 0"):
        PiiEntityMatch(
            entity_type="EMAIL",
            start_idx=-1,
            end_idx=10,
            masked_value="[REDACTED_EMAIL]",
            original_preview="abc",
        )

    with pytest.raises(ValueError, match="El end_idx debe ser estrictamente mayor que start_idx"):
        PiiEntityMatch(
            entity_type="EMAIL",
            start_idx=10,
            end_idx=10,
            masked_value="[REDACTED_EMAIL]",
            original_preview="abc",
        )

    with pytest.raises(ValueError, match="El end_idx debe ser estrictamente mayor que start_idx"):
        PiiEntityMatch(
            entity_type="EMAIL",
            start_idx=15,
            end_idx=10,
            masked_value="[REDACTED_EMAIL]",
            original_preview="abc",
        )


def test_pii_entity_match_empty_fields() -> None:
    with pytest.raises(ValueError, match="El entity_type no puede estar vacío"):
        PiiEntityMatch(
            entity_type="",
            start_idx=0,
            end_idx=5,
            masked_value="[REDACTED]",
            original_preview="abc",
        )

    with pytest.raises(ValueError, match="El masked_value no puede estar vacío"):
        PiiEntityMatch(
            entity_type="EMAIL",
            start_idx=0,
            end_idx=5,
            masked_value="",
            original_preview="abc",
        )
