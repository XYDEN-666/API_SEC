"""SQL injection indicator scanner tests using the smoke-test harness."""

import asyncio

from app.scanners.sqli_indicators import SQLiScanner
from tests.scanner_harness import run_scanner_against_target


def _scan(base_url, path="/", parameters=None):
    return asyncio.run(
        run_scanner_against_target(
            SQLiScanner(), base_url, path=path, parameters=parameters
        )
    )


def test_error_echoing_fixture_produces_finding(http_sqli_target) -> None:
    base_url = http_sqli_target(vulnerable=True)

    path_findings = _scan(base_url, path="/users/{user_id}")
    assert any(
        "SQL injection indicator" in finding.title
        for finding in path_findings
    )
    finding = next(
        f for f in path_findings if "SQL injection indicator" in f.title
    )
    assert finding.severity.value == "high"
    assert finding.owasp_category == "api10:2023"
    assert (
        "sqlstate" in finding.evidence.lower()
        or "syntax error" in finding.evidence.lower()
    )

    query_findings = _scan(
        base_url,
        path="/search",
        parameters=[{"name": "q", "in": "query"}],
    )
    assert any(
        "SQL injection indicator" in finding.title
        for finding in query_findings
    )


def test_parameterized_fixture_produces_no_findings(http_sqli_target) -> None:
    base_url = http_sqli_target(vulnerable=False)

    assert _scan(base_url, path="/users/{user_id}") == []
    assert (
        _scan(
            base_url,
            path="/search",
            parameters=[{"name": "q", "in": "query"}],
        )
        == []
    )
