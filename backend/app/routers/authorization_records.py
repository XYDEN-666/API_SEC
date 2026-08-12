"""Authorization record CRUD routes, scoped to the owning project."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import AuthorizationRecord, Project, User
from app.routers.projects import get_owned_project
from app.schemas.authorization_record import (
    AuthorizationRecordCreate,
    AuthorizationRecordResponse,
    AuthorizationRecordUpdate,
)

router = APIRouter(tags=["authorization-records"])


async def _get_owned_record(
    record_id: int,
    owner: User,
    session: AsyncSession,
) -> AuthorizationRecord:
    record = await session.scalar(
        select(AuthorizationRecord)
        .join(Project, Project.id == AuthorizationRecord.project_id)
        .where(
            AuthorizationRecord.id == record_id,
            Project.owner_id == owner.id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authorization record not found",
        )
    return record


@router.post(
    "/projects/{project_id}/authorization-records",
    response_model=AuthorizationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_authorization_record(
    project_id: int,
    payload: AuthorizationRecordCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuthorizationRecord:
    project = await get_owned_project(project_id, current_user, session)
    record = AuthorizationRecord(
        project_id=project.id,
        description=payload.description,
        scope_notes=payload.scope_notes,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


@router.get(
    "/projects/{project_id}/authorization-records",
    response_model=list[AuthorizationRecordResponse],
)
async def list_authorization_records(
    project_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AuthorizationRecord]:
    project = await get_owned_project(project_id, current_user, session)
    records = await session.scalars(
        select(AuthorizationRecord)
        .where(AuthorizationRecord.project_id == project.id)
        .order_by(AuthorizationRecord.id)
    )
    return list(records)


@router.get(
    "/authorization-records/{record_id}",
    response_model=AuthorizationRecordResponse,
)
async def get_authorization_record(
    record_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuthorizationRecord:
    return await _get_owned_record(record_id, current_user, session)


@router.put(
    "/authorization-records/{record_id}",
    response_model=AuthorizationRecordResponse,
)
async def update_authorization_record(
    record_id: int,
    payload: AuthorizationRecordUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuthorizationRecord:
    record = await _get_owned_record(record_id, current_user, session)
    record.description = payload.description
    record.scope_notes = payload.scope_notes
    await session.commit()
    await session.refresh(record)
    return record


@router.delete(
    "/authorization-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_authorization_record(
    record_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    record = await _get_owned_record(record_id, current_user, session)
    await session.delete(record)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
