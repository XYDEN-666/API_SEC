"""Risk scoring: combine finding severity and confidence into a 0-10 score.

Scoring model
-------------
Severity contributes a base weight on a 0-10 scale and confidence acts as a
multiplier:

    severity weights:   INFO=2, LOW=4, MEDIUM=6, HIGH=8, CRITICAL=10
    confidence weights: LOW=0.5, MEDIUM=0.75, HIGH=1.0

    score = round(severity_weight * confidence_weight, 1)
    score = clamp(score, 0.0, 10.0)

Risk labels (lower bound inclusive, upper bound exclusive):

    Low:      0.0 <= score <  4.0
    Medium:   4.0 <= score <  6.0
    High:     6.0 <= score <  8.0
    Critical: 8.0 <= score <= 10.0

This keeps the bands deterministic at the boundaries: a score of exactly 4.0
is Medium, 6.0 is High, and 8.0 is Critical.

Inputs may be the :class:`~app.scanners.base.Severity` /
:class:`~app.scanners.base.Confidence` enums or their string values (e.g.
``"high"``), so the helpers work on both in-memory scanner findings and
persisted rows.
"""

from dataclasses import dataclass

from app.scanners.base import Confidence, Severity

_SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.INFO: 2.0,
    Severity.LOW: 4.0,
    Severity.MEDIUM: 6.0,
    Severity.HIGH: 8.0,
    Severity.CRITICAL: 10.0,
}

_CONFIDENCE_WEIGHTS: dict[Confidence, float] = {
    Confidence.LOW: 0.5,
    Confidence.MEDIUM: 0.75,
    Confidence.HIGH: 1.0,
}

# Band boundaries; lower bound inclusive, upper bound exclusive.
_MEDIUM_FLOOR = 4.0
_HIGH_FLOOR = 6.0
_CRITICAL_FLOOR = 8.0


def _as_severity(severity: Severity | str) -> Severity:
    if isinstance(severity, Severity):
        return severity
    return Severity(severity)


def _as_confidence(confidence: Confidence | str) -> Confidence:
    if isinstance(confidence, Confidence):
        return confidence
    return Confidence(confidence)


def risk_score(severity: Severity | str, confidence: Confidence | str) -> float:
    """Return a numeric risk score in ``[0.0, 10.0]`` (one decimal)."""
    severity = _as_severity(severity)
    confidence = _as_confidence(confidence)
    raw = _SEVERITY_WEIGHTS[severity] * _CONFIDENCE_WEIGHTS[confidence]
    return round(max(0.0, min(10.0, raw)), 1)


def risk_label(score: float) -> str:
    """Map a score to ``Low`` / ``Medium`` / ``High`` / ``Critical``."""
    if score >= _CRITICAL_FLOOR:
        return "Critical"
    if score >= _HIGH_FLOOR:
        return "High"
    if score >= _MEDIUM_FLOOR:
        return "Medium"
    return "Low"


@dataclass(frozen=True)
class RiskAssessment:
    """Numeric score plus its human-readable label."""

    score: float
    label: str


def assess(severity: Severity | str, confidence: Confidence | str) -> RiskAssessment:
    """Combine severity and confidence into a :class:`RiskAssessment`."""
    score = risk_score(severity, confidence)
    return RiskAssessment(score=score, label=risk_label(score))
