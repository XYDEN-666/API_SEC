"""Scan trigger routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Scan, Target, User
from app.routers.projects import get_owned_project
from app.schemas.scan import ScanResponse
from app.tasks.scans import run_scan

router = APIRouter(tags=["scans"])


async def get_owned_scan(
    scan_id: int,
    owner: User,
    session: AsyncSession,
) -> Scan:
    """Load a scan and enforce ownership through its target's project."""
    scan = await session.scalar(select(Scan).where(Scan.id == scan_id))
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )
    target = await session.scalar(
        select(Target).where(Target.id == scan.target_id)
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )
    await get_owned_project(target.project_id, owner, session)
    return scan


@router.get(
    "/targets/{target_id}/scans",
    response_model=list[ScanResponse],
)
async def list_target_scans(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Scan]:
    """List a target's scans, newest first."""
    target = await session.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    await get_owned_project(target.project_id, current_user, session)
    scans = (
        await session.scalars(
            select(Scan)
            .where(Scan.target_id == target_id)
            .order_by(Scan.id.desc())
        )
    ).all()
    return list(scans)


@router.post("/targets/{target_id}/scans", status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Enqueue a background scan for the target and return its task id."""
    target = await session.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    await get_owned_project(target.project_id, current_user, session)

    task = run_scan.delay(target_id)
    return {"scan_id": task.id, "status": "queued"}
