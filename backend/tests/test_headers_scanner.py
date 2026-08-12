"""Security Headers scanner tests using the smoke-test harness."""

import asyncio

from app.scanners.headers import HeaderScanner
from tests.scanner_harness import run_scanner_against_target

ALL_SECURE_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'self'",
    "X-Frame-Options": "DENY",
}


def _scan(scanner, base_url):
    return asyncio.run(run_scanner_against_target(scanner, base_url))


def test_missing_hsts_produces_finding(http_target_factory) -> None:
    # All headers present except Strict-Transport-Security.
    headers = dict(ALL_SECURE_HEADERS)
    del headers["Strict-Transport-Security"]
    base_url = http_target_factory(headers)

    findings = _scan(HeaderScanner(), base_url)
    titles = [finding.title for finding in findings]

    assert any(
        "Strict-Transport-Security" in title for title in titles
    ), f"HSTS finding expected, got {titles}"
    hsts_finding = next(
        finding
        for finding in findings
        if "Strict-Transport-Security" in finding.title
    )
    assert hsts_finding.owasp_category == "api8:2023"
    assert hsts_finding.severity.value == "medium"


def test_all_headers_present_produces_no_findings(http_target_factory) -> None:
    base_url = http_target_factory(ALL_SECURE_HEADERS)

    findings = _scan(HeaderScanner(), base_url)
    assert findings == []


def test_misconfigured_headers_produce_findings(http_target_factory) -> None:
    base_url = http_target_factory(
        {
            "Strict-Transport-Security": "max-age=0",
            "X-Content-Type-Options": "text/html",
            "X-Frame-Options": "ALLOWALL",
            # Content-Security-Policy intentionally missing.
        }
    )

    findings = _scan(HeaderScanner(), base_url)
    titles = {finding.title for finding in findings}

    assert "Misconfigured Strict-Transport-Security" in titles
    assert "Misconfigured X-Content-Type-Options" in titles
    assert "Missing Content-Security-Policy" in titles
    assert "Misconfigured X-Frame-Options" in titles
    assert all(finding.owasp_category == "api8:2023" for finding in findings)
