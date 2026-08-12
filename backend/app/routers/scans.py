"""Scan trigger routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Target, User
from app.routers.projects import get_owned_project
from app.tasks.scans import run_scan

router = APIRouter(tags=["scans"])


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
