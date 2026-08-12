"""HTML report tests (Task 11.1)."""

from app.scanners.base import BaseScanner, Confidence, Finding as ScannerFinding, Severity
from tests.report_fixtures import (
    ReportScanner,
    _auth,
    _email,
    _register,
    create_target_with_endpoint,
    run_scan,
)


class NoopScanner(BaseScanner):
    name = "noop"
    description = "Finds nothing."

    async def scan(self, target, endpoint, credentials):
        return []


def test_report_html_renders_summary_categories_and_evidence(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = create_target_with_endpoint(client, token)
    scan_id = run_scan(target_id, ReportScanner())

    response = client.get(f"/scans/{scan_id}/report.html", headers=_auth(token))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text

    # Readable report shell.
    assert "APIShield Scan Report" in html
    assert "Report API" in html
    assert "http://127.0.0.1:9" in html
    assert "completed" in html

    # Summary section with counts by severity.
    assert "Summary" in html
    assert "<td>Critical</td><td>0</td>" in html
    assert "<td>High</td><td>1</td>" in html
    assert "<td>Medium</td><td>1</td>" in html
    assert "<td>Low</td><td>0</td>" in html
    assert "<td>Info</td><td>1</td>" in html
    assert "<td><strong>Total</strong></td><td><strong>3</strong></td>" in html

    # Findings grouped by OWASP category with human-readable labels.
    assert "API8:2023 Security Misconfiguration" in html
    assert "API2:2023 Broken Authentication" in html
    assert "Missing HSTS header" in html
    assert "JWT missing exp claim" in html
    assert "Informational note" in html

    # Risk score/labels from the Task 10.3 service.
    assert "Risk: Critical (8.0/10)" in html
    assert "Risk: Medium (4.5/10)" in html
    assert "Risk: Low (1.0/10)" in html

    # Evidence excerpts (request/response captured by the orchestrator).
    assert "GET http://127.0.0.1:9/health" in html
    assert "report_fixture" in html


def test_report_html_renders_empty_scan(client, unique_email) -> None:
    _, token = _register(client, _email("owner"))
    target_id = create_target_with_endpoint(client, token)
    scan_id = run_scan(target_id, NoopScanner())

    response = client.get(f"/scans/{scan_id}/report.html", headers=_auth(token))
    assert response.status_code == 200
    html = response.text
    assert "No findings for this scan." in html
    assert "<td><strong>Total</strong></td><td><strong>0</strong></td>" in html


def test_report_html_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = create_target_with_endpoint(client, owner_token)
    scan_id = run_scan(target_id, ReportScanner())

    assert (
        client.get(f"/scans/{scan_id}/report.html").status_code == 401
    )
    assert (
        client.get(
            f"/scans/{scan_id}/report.html", headers=_auth(other_token)
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/scans/999999/report.html", headers=_auth(owner_token)
        ).status_code
        == 404
    )
