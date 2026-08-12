"""Findings read routes (Task 10.5)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Finding, User
from app.routers.scans import get_owned_scan
from app.schemas.finding import FindingResponse
from app.services.risk_scoring import risk_label, risk_score

router = APIRouter(tags=["findings"])


@router.get("/scans/{scan_id}/findings", response_model=list[FindingResponse])
async def list_scan_findings(
    scan_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FindingResponse]:
    """Return a scan's findings with severity, OWASP category and risk score.

    Findings are read back from the persistence layer, so the result is
    deduplicated by construction: true duplicates were collapsed when the
    scan ran, while per-endpoint findings remain distinct.
    """
    await get_owned_scan(scan_id, current_user, session)

    rows = (
        await session.scalars(
            select(Finding)
            .where(Finding.scan_id == scan_id)
            .order_by(Finding.id)
        )
    ).all()
    return [
        FindingResponse(
            id=row.id,
            scan_id=row.scan_id,
            title=row.title,
            description=row.description,
            severity=row.severity,
            endpoint=row.endpoint,
            evidence_id=row.evidence_id,
            owasp_category=row.owasp_category,
            confidence=row.confidence,
            created_at=row.created_at,
            risk_score=risk_score(row.severity, row.confidence),
            risk_label=risk_label(risk_score(row.severity, row.confidence)),
        )
        for row in rows
    ]
