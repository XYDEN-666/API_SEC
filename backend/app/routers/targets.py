"""Target CRUD routes, scoped to the owning project."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Project, Target, User
from app.routers.projects import get_owned_project
from app.schemas.target import TargetCreate, TargetResponse, TargetUpdate

router = APIRouter(tags=["targets"])


async def _get_owned_target(
    target_id: int,
    owner: User,
    session: AsyncSession,
) -> Target:
    target = await session.scalar(
        select(Target)
        .join(Project, Project.id == Target.project_id)
        .where(
            Target.id == target_id,
            Project.owner_id == owner.id,
        )
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    return target


@router.post(
    "/projects/{project_id}/targets",
    response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_target(
    project_id: int,
    payload: TargetCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Target:
    project = await get_owned_project(project_id, current_user, session)
    target = Target(
        project_id=project.id,
        name=payload.name,
        base_url=payload.base_url,
    )
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return target


@router.get(
    "/projects/{project_id}/targets",
    response_model=list[TargetResponse],
)
async def list_targets(
    project_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Target]:
    project = await get_owned_project(project_id, current_user, session)
    targets = await session.scalars(
        select(Target)
        .where(Target.project_id == project.id)
        .order_by(Target.id)
    )
    return list(targets)


@router.get("/targets/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Target:
    return await _get_owned_target(target_id, current_user, session)


@router.put("/targets/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: int,
    payload: TargetUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Target:
    target = await _get_owned_target(target_id, current_user, session)
    target.name = payload.name
    target.base_url = payload.base_url
    await session.commit()
    await session.refresh(target)
    return target


@router.delete("/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    target = await _get_owned_target(target_id, current_user, session)
    await session.delete(target)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
