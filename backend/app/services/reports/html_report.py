"""HTML report generation (Task 11.1)."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.owasp_mapping import category_label
from app.services.reports.data import ReportData

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_html_report(data: ReportData) -> str:
    """Render a scan's report data to a standalone HTML document."""
    template = _ENV.get_template("report.html.j2")
    return template.render(data=data, category_label=category_label)
