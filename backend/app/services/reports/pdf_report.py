"""PDF report generation (Task 11.2).

The PDF is WeasyPrint's rendering of the exact HTML produced by
``html_report.render_html_report`` -- there is no separate PDF template, so
the two formats cannot drift apart.

WeasyPrint needs native GTK/Pango libraries. They are installed in the
project's Docker image but are not present on every developer machine, and
``import weasyprint`` raises ``OSError`` when they are missing. Importing it
at module scope therefore took the whole API down with it, so the import is
deferred to call time: the app and every non-PDF route start regardless, and
only PDF export reports a clear error.
"""


def render_pdf_report(html: str) -> bytes:
    """Render an HTML report to PDF bytes via WeasyPrint."""
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "PDF export needs the WeasyPrint native libraries (GTK/Pango). "
            "Run the backend in Docker, or install them for your platform: "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        ) from exc
    return HTML(string=html).write_pdf()
