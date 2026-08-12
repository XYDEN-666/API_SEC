"""PDF report generation (Task 11.2).

The PDF is WeasyPrint's rendering of the exact HTML produced by
``html_report.render_html_report`` -- there is no separate PDF template, so
the two formats cannot drift apart.
"""

from weasyprint import HTML


def render_pdf_report(html: str) -> bytes:
    """Render an HTML report to PDF bytes via WeasyPrint."""
    return HTML(string=html).write_pdf()
