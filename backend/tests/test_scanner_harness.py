"""Scanner harness example tests."""

import asyncio

import httpx

from app.scanners.base import BaseScanner, Confidence, Finding, Severity
from tests.scanner_harness import run_scanner_against_target


class DummyScanner(BaseScanner):
    """A dummy scanner that really talks to the fixture target."""

    name = "dummy"
    description = "Example no-op scanner for the smoke-test harness."

    async def scan(self, target, endpoint, credentials):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{target.base_url}{endpoint.path}")
        return [
            Finding(
                title="Dummy finding",
                description="Example finding from the smoke-test scanner.",
                severity=Severity.INFO,
                evidence=f"GET {endpoint.path} -> {response.status_code}",
                owasp_category="api5:2023",
                confidence=Confidence.MEDIUM,
            )
        ]


class NoOpScanner(BaseScanner):
    name = "noop"
    description = "Returns no findings."

    async def scan(self, target, endpoint, credentials):
        return []


def test_harness_runs_dummy_scanner(http_target) -> None:
    findings = asyncio.run(
        run_scanner_against_target(DummyScanner(), http_target)
    )

    assert len(findings) == 1
    assert findings[0].title == "Dummy finding"
    assert "200" in findings[0].evidence


def test_harness_accepts_noop_empty_result(http_target) -> None:
    findings = asyncio.run(
        run_scanner_against_target(NoOpScanner(), http_target)
    )
    assert findings == []
