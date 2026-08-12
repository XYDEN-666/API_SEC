"""CORS scanner tests using the smoke-test harness."""

import asyncio

from app.scanners.cors import CORSScanner
from tests.scanner_harness import run_scanner_against_target


def _scan(scanner, base_url):
    return asyncio.run(run_scanner_against_target(scanner, base_url))


def _titles(findings):
    return [finding.title for finding in findings]


def test_wildcard_with_credentials_produces_finding(
    http_target_factory,
) -> None:
    base_url = http_target_factory(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

    findings = _scan(CORSScanner(), base_url)
    titles = _titles(findings)

    assert any("Wildcard" in title for title in titles)
    finding = next(
        f for f in findings if "Wildcard" in f.title and "credentials" in f.title
    )
    assert finding.severity.value == "high"
    assert finding.owasp_category == "api8:2023"


def test_restricted_cors_produces_no_findings(http_target_factory) -> None:
    base_url = http_target_factory(
        {
            "Access-Control-Allow-Origin": "https://trusted.example",
            "Access-Control-Allow-Credentials": "true",
        }
    )

    assert _scan(CORSScanner(), base_url) == []


def test_no_cors_headers_produce_no_findings(http_target_factory) -> None:
    base_url = http_target_factory({})

    assert _scan(CORSScanner(), base_url) == []


def test_wildcard_without_credentials_is_medium(http_target_factory) -> None:
    base_url = http_target_factory({"Access-Control-Allow-Origin": "*"})

    findings = _scan(CORSScanner(), base_url)
    assert len(findings) == 1
    assert findings[0].title == "Wildcard CORS origin"
    assert findings[0].severity.value == "medium"


def test_attacker_origin_with_credentials_is_high(http_target_factory) -> None:
    base_url = http_target_factory(
        {
            "Access-Control-Allow-Origin": "https://evil.example",
            "Access-Control-Allow-Credentials": "true",
        }
    )

    findings = _scan(CORSScanner(), base_url)
    assert any("Reflected" in finding.title for finding in findings)
    reflected = next(f for f in findings if "Reflected" in f.title)
    assert reflected.severity.value == "high"
