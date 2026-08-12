"""Risk scoring unit tests (Task 10.3)."""

import pytest

from app.scanners.base import Confidence, Severity
from app.services.risk_scoring import (
    RiskAssessment,
    assess,
    risk_label,
    risk_score,
)


def test_full_severity_confidence_matrix() -> None:
    """Every severity x confidence combination maps to an expected score and
    label, so the weighting scheme is fully pinned down."""
    expected = {
        (Severity.INFO, Confidence.LOW): (1.0, "Low"),
        (Severity.INFO, Confidence.MEDIUM): (1.5, "Low"),
        (Severity.INFO, Confidence.HIGH): (2.0, "Low"),
        (Severity.LOW, Confidence.LOW): (2.0, "Low"),
        (Severity.LOW, Confidence.MEDIUM): (3.0, "Low"),
        (Severity.LOW, Confidence.HIGH): (4.0, "Medium"),
        (Severity.MEDIUM, Confidence.LOW): (3.0, "Low"),
        (Severity.MEDIUM, Confidence.MEDIUM): (4.5, "Medium"),
        (Severity.MEDIUM, Confidence.HIGH): (6.0, "High"),
        (Severity.HIGH, Confidence.LOW): (4.0, "Medium"),
        (Severity.HIGH, Confidence.MEDIUM): (6.0, "High"),
        (Severity.HIGH, Confidence.HIGH): (8.0, "Critical"),
        (Severity.CRITICAL, Confidence.LOW): (5.0, "Medium"),
        (Severity.CRITICAL, Confidence.MEDIUM): (7.5, "High"),
        (Severity.CRITICAL, Confidence.HIGH): (10.0, "Critical"),
    }
    for (severity, confidence), (score, label) in expected.items():
        assert risk_score(severity, confidence) == score
        assert risk_label(risk_score(severity, confidence)) == label


def test_scores_stay_within_zero_to_ten() -> None:
    scores = [
        risk_score(severity, confidence)
        for severity in Severity
        for confidence in Confidence
    ]
    assert min(scores) >= 0.0
    assert max(scores) <= 10.0
    assert max(scores) == 10.0  # CRITICAL + HIGH
    assert min(scores) == 1.0  # INFO + LOW


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.0, "Low"),
        (3.9, "Low"),
        (4.0, "Medium"),  # lower bound of Medium is inclusive
        (5.9, "Medium"),
        (6.0, "High"),  # lower bound of High is inclusive
        (7.9, "High"),
        (8.0, "Critical"),  # lower bound of Critical is inclusive
        (10.0, "Critical"),
    ],
)
def test_risk_label_band_boundaries(score: float, label: str) -> None:
    assert risk_label(score) == label


def test_string_values_are_equivalent_to_enums() -> None:
    assert risk_score("high", "medium") == risk_score(
        Severity.HIGH, Confidence.MEDIUM
    )
    assert risk_score("low", "high") == risk_score(
        Severity.LOW, Confidence.HIGH
    )


def test_assess_returns_score_and_label_together() -> None:
    result = assess(Severity.CRITICAL, Confidence.HIGH)
    assert isinstance(result, RiskAssessment)
    assert result.score == 10.0
    assert result.label == "Critical"

    result = assess("medium", "low")
    assert result.score == 3.0
    assert result.label == "Low"


def test_invalid_input_raises_value_error() -> None:
    with pytest.raises(ValueError):
        risk_score("catastrophic", Confidence.HIGH)
    with pytest.raises(ValueError):
        risk_score(Severity.HIGH, "definitely")
