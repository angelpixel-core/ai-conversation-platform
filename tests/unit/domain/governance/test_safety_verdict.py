"""Unit tests for SafetyVerdict Value Object."""

from dataclasses import FrozenInstanceError

import pytest
from src.domain.governance.value_objects.safety_verdict import SafetyVerdict


def test_safety_verdict_safe_creation() -> None:
    verdict = SafetyVerdict.safe()
    assert verdict.is_safe is True
    assert verdict.violation_type is None
    assert verdict.risk_score == 0.0
    assert verdict.matched_rule is None
    assert verdict.details == {}


def test_safety_verdict_violation_creation() -> None:
    verdict = SafetyVerdict.violation(
        violation_type="PROMPT_INJECTION",
        risk_score=0.95,
        matched_rule="JAILBREAK_ATTEMPT",
        details={"matched_keyword": "IGNORE PREVIOUS INSTRUCTIONS"},
    )
    assert verdict.is_safe is False
    assert verdict.violation_type == "PROMPT_INJECTION"
    assert verdict.risk_score == 0.95
    assert verdict.matched_rule == "JAILBREAK_ATTEMPT"
    assert verdict.details["matched_keyword"] == "IGNORE PREVIOUS INSTRUCTIONS"


def test_safety_verdict_immutability() -> None:
    verdict = SafetyVerdict.safe()
    with pytest.raises(FrozenInstanceError):
        verdict.is_safe = False  # type: ignore[misc]


def test_safety_verdict_invalid_risk_score() -> None:
    with pytest.raises(ValueError, match="El risk_score debe estar entre 0.0 y 1.0"):
        SafetyVerdict(
            is_safe=False,
            violation_type="TOXICITY",
            risk_score=1.5,
            matched_rule="TOXIC_CONTENT",
        )

    with pytest.raises(ValueError, match="El risk_score debe estar entre 0.0 y 1.0"):
        SafetyVerdict(
            is_safe=False,
            violation_type="TOXICITY",
            risk_score=-0.1,
            matched_rule="TOXIC_CONTENT",
        )


def test_safety_verdict_inconsistent_safe_with_violation_type() -> None:
    with pytest.raises(ValueError, match="Un veredicto seguro no puede contener violation_type"):
        SafetyVerdict(
            is_safe=True,
            violation_type="PROMPT_INJECTION",
            risk_score=0.0,
            matched_rule=None,
        )


def test_safety_verdict_inconsistent_unsafe_without_violation_type() -> None:
    with pytest.raises(ValueError, match="Un veredicto inseguro debe especificar violation_type"):
        SafetyVerdict(
            is_safe=False,
            violation_type=None,
            risk_score=0.8,
            matched_rule="RULE_1",
        )
