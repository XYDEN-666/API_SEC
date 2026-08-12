"""Report export routes: HTML, PDF, and JSON (Tasks 11.1-11.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import User
from app.routers.scans import get_owned_scan
from app.schemas.report import ReportResponse
from app.services.reports.data import build_report_data
from app.services.reports.html_report import render_html_report
from app.services.reports.pdf_report import render_pdf_report

router = APIRouter(tags=["reports"])


@router.get("/scans/{scan_id}/report.html", response_class=HTMLResponse)
async def scan_report_html(
    scan_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> HTMLResponse:
    """Return a rendered HTML report for a completed scan."""
    await get_owned_scan(scan_id, current_user, session)
    data = await build_report_data(session, scan_id)
    return HTMLResponse(render_html_report(data))


@router.get("/scans/{scan_id}/report.pdf")
async def scan_report_pdf(
    scan_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Return the PDF rendering of the same HTML report."""
    await get_owned_scan(scan_id, current_user, session)
    data = await build_report_data(session, scan_id)
    pdf = render_pdf_report(render_html_report(data))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="scan-{scan_id}-report.pdf"'
            )
        },
    )


@router.get("/scans/{scan_id}/report.json", response_model=ReportResponse)
async def scan_report_json(
    scan_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportResponse:
    """Return the full findings, evidence and metadata as structured JSON."""
    await get_owned_scan(scan_id, current_user, session)
    data = await build_report_data(session, scan_id)
    return ReportResponse.model_validate(data)
