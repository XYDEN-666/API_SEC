"""HTTP Methods scanner tests using the smoke-test harness."""

import asyncio

from app.scanners.http_methods import HTTPMethodScanner
from tests.scanner_harness import run_scanner_against_target


def _scan(scanner, base_url):
    return asyncio.run(run_scanner_against_target(scanner, base_url))


def test_trace_enabled_produces_finding(http_target_factory) -> None:
    base_url = http_target_factory({}, allow_methods=["TRACE"])

    findings = _scan(HTTPMethodScanner(), base_url)
    titles = {finding.title for finding in findings}

    assert "TRACE method enabled" in titles
    trace = next(f for f in findings if f.title == "TRACE method enabled")
    assert trace.severity.value == "high"
    assert trace.owasp_category == "api8:2023"
    # PUT/DELETE are not enabled on this fixture.
    assert "PUT method enabled" not in titles
    assert "DELETE method enabled" not in titles


def test_put_and_delete_enabled_produce_findings(http_target_factory) -> None:
    base_url = http_target_factory({}, allow_methods=["PUT", "DELETE"])

    findings = _scan(HTTPMethodScanner(), base_url)
    titles = {finding.title for finding in findings}

    assert "PUT method enabled" in titles
    assert "DELETE method enabled" in titles
    put = next(f for f in findings if f.title == "PUT method enabled")
    assert put.severity.value == "medium"


def test_no_extra_methods_produces_no_findings(http_target_factory) -> None:
    base_url = http_target_factory({})

    findings = _scan(HTTPMethodScanner(), base_url)
    assert findings == []
