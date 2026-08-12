"""JSON report tests (Task 11.3)."""

from app.schemas.report import ReportResponse
from tests.report_fixtures import (
    ReportScanner,
    _auth,
    _email,
    _register,
    create_target_with_endpoint,
    run_scan,
)


def test_report_json_validates_and_matches_findings_api(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = create_target_with_endpoint(client, token)
    scan_id = run_scan(target_id, ReportScanner())

    response = client.get(f"/scans/{scan_id}/report.json", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()

    # The payload validates against the defined schema.
    report = ReportResponse.model_validate(body)

    # Metadata.
    assert report.metadata.scan_id == scan_id
    assert report.metadata.target_name == "Report API"
    assert report.metadata.base_url == "http://127.0.0.1:9"
    assert report.metadata.project_name == "Report Project"
    assert report.metadata.status == "completed"
    assert report.metadata.started_at is not None
    assert report.metadata.finished_at is not None
    assert report.metadata.generated_at is not None

    # Summary counts match the persisted findings.
    assert report.summary.high == 1
    assert report.summary.medium == 1
    assert report.summary.info == 1
    assert report.summary.low == 0
    assert report.summary.critical == 0
    assert report.summary.total == 3

    # Every finding carries evidence, risk scoring and category.
    assert len(report.findings) == 3
    titles = {finding.title for finding in report.findings}
    assert titles == {
        "Missing HSTS header",
        "JWT missing exp claim",
        "Informational note",
    }
    by_title = {finding.title: finding for finding in report.findings}
    assert by_title["Missing HSTS header"].risk_score == 8.0
    assert by_title["Missing HSTS header"].risk_label == "Critical"
    assert by_title["Missing HSTS header"].owasp_category == "api8:2023"
    assert by_title["JWT missing exp claim"].risk_score == 4.5
    assert by_title["JWT missing exp claim"].risk_label == "Medium"
    assert by_title["JWT missing exp claim"].owasp_category == "api2:2023"
    assert by_title["Informational note"].risk_score == 1.0
    assert by_title["Informational note"].risk_label == "Low"

    for finding in report.findings:
        assert finding.evidence is not None
        assert finding.evidence.evidence_id == finding.evidence_id
        assert finding.evidence.scanner_name == "report_fixture"
        assert finding.evidence.request_data == "GET http://127.0.0.1:9/health"
        assert finding.evidence.response_data is not None
        assert finding.evidence.timestamp is not None

    # Includes every finding present in the HTML report.
    html = client.get(f"/scans/{scan_id}/report.html", headers=_auth(token))
    assert html.status_code == 200
    for title in titles:
        assert title in html.text

    # Matches the findings API exactly (same set of finding ids/titles).
    api = client.get(f"/scans/{scan_id}/findings", headers=_auth(token))
    assert api.status_code == 200
    api_findings = api.json()
    assert {item["id"] for item in api_findings} == {
        finding.id for finding in report.findings
    }
    assert {item["title"] for item in api_findings} == titles


def test_report_json_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = create_target_with_endpoint(client, owner_token)
    scan_id = run_scan(target_id, ReportScanner())

    assert client.get(f"/scans/{scan_id}/report.json").status_code == 401
    assert (
        client.get(
            f"/scans/{scan_id}/report.json", headers=_auth(other_token)
        ).status_code
        == 404
    )
