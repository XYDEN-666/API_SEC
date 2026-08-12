"""BaseScanner interface and Finding schema tests."""

import asyncio

import pytest

from app.models import Credential, Endpoint, Target
from app.scanners.base import (
    BaseScanner,
    Confidence,
    Finding,
    Severity,
)


def _target() -> Target:
    return Target(
        project_id=1,
        base_url="https://api.example.com",
        name="API",
    )


def _endpoint() -> Endpoint:
    return Endpoint(
        target_id=1,
        path="/health",
        method="GET",
        parameters=None,
    )


def _credential() -> Credential:
    return Credential(
        target_id=1,
        identity_name="ci-bot",
        auth_type="api_key",
        encrypted_value="gAAAA-encrypted-placeholder",
    )


def test_finding_carries_all_standard_fields() -> None:
    finding = Finding(
        title="Missing X-Frame-Options",
        description="The endpoint does not send X-Frame-Options.",
        severity=Severity.MEDIUM,
        evidence="GET /health returned no X-Frame-Options header",
        owasp_category="api5:2023",
        confidence=Confidence.HIGH,
    )

    assert finding.title == "Missing X-Frame-Options"
    assert finding.description.startswith("The endpoint")
    assert finding.severity == Severity.MEDIUM
    assert finding.severity.value == "medium"
    assert "X-Frame-Options" in finding.evidence
    assert finding.owasp_category == "api5:2023"
    assert finding.confidence == Confidence.HIGH
    assert finding.confidence.value == "high"


def test_base_scanner_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseScanner()  # type: ignore[abstract]


def test_subclass_without_scan_cannot_be_instantiated() -> None:
    class IncompleteScanner(BaseScanner):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteScanner()


def test_new_scanner_implements_only_scan() -> None:
    class HeaderScanner(BaseScanner):
        name = "headers"
        description = "Checks for missing security response headers."

        async def scan(self, target, endpoint, credentials):
            return [
                Finding(
                    title="Missing X-Frame-Options",
                    description=(
                        "The endpoint does not send X-Frame-Options."
                    ),
                    severity=Severity.LOW,
                    evidence="no X-Frame-Options header on response",
                    owasp_category="api5:2023",
                    confidence=Confidence.HIGH,
                )
            ]

    scanner = HeaderScanner()
    assert scanner.name == "headers"
    assert scanner.description.startswith("Checks")

    findings = asyncio.run(
        scanner.scan(_target(), _endpoint(), _credential())
    )

    assert len(findings) == 1
    assert findings[0].title == "Missing X-Frame-Options"
    assert findings[0].severity == Severity.LOW


def test_empty_findings_means_no_issues() -> None:
    class CleanScanner(BaseScanner):
        name = "clean"
        description = "Always passes."

        async def scan(self, target, endpoint, credentials):
            return []

    assert asyncio.run(CleanScanner().scan(_target(), None, None)) == []
