"""PDF report tests (Task 11.2)."""

import io

from pypdf import PdfReader

from tests.report_fixtures import (
    ReportScanner,
    _auth,
    _email,
    _register,
    create_target_with_endpoint,
    run_scan,
)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_report_pdf_renders_and_matches_html_content(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = create_target_with_endpoint(client, token)
    scan_id = run_scan(target_id, ReportScanner())

    response = client.get(f"/scans/{scan_id}/report.pdf", headers=_auth(token))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    pdf = response.content
    assert pdf.startswith(b"%PDF")

    text = _extract_pdf_text(pdf)
    assert "APIShield Scan Report" in text
    assert "Summary" in text
    assert "API8:2023 Security Misconfiguration" in text
    assert "API2:2023 Broken Authentication" in text
    assert "Missing HSTS header" in text
    assert "JWT missing exp claim" in text
    assert "Informational note" in text
    assert "Risk: Critical" in text

    # Same content as the HTML version: every finding title present in HTML
    # must appear in the PDF text.
    html_response = client.get(
        f"/scans/{scan_id}/report.html", headers=_auth(token)
    )
    assert html_response.status_code == 200
    for title in (
        "Missing HSTS header",
        "JWT missing exp claim",
        "Informational note",
    ):
        assert title in html_response.text
        assert title in text, f"{title!r} missing from PDF text"


def test_report_pdf_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = create_target_with_endpoint(client, owner_token)
    scan_id = run_scan(target_id, ReportScanner())

    assert client.get(f"/scans/{scan_id}/report.pdf").status_code == 401
    assert (
        client.get(
            f"/scans/{scan_id}/report.pdf", headers=_auth(other_token)
        ).status_code
        == 404
    )
