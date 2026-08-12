"""Report generation: HTML (Jinja2), PDF (WeasyPrint), and JSON export."""

from app.services.reports.data import build_report_data

__all__ = ["build_report_data"]
