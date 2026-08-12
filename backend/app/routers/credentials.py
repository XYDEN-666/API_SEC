"""Credential CRUD routes.

Secrets are encrypted at rest and never returned by the API — responses only
carry a masked placeholder. Decryption is reserved for internal service calls.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_value
from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Credential, Project, Target, User
from app.routers.projects import get_owned_project
from app.schemas.credential import CredentialCreate, CredentialResponse

router = APIRouter(tags=["credentials"])

_MASKED_VALUE = "••••••••"


def _to_response(credential: Credential) -> CredentialResponse:
    return CredentialResponse(
        id=credential.id,
        target_id=credential.target_id,
        identity_name=credential.identity_name,
        auth_type=credential.auth_type,
        masked_value=_MASKED_VALUE,
    )


async def _get_owned_credential(
    target_id: int,
    credential_id: int,
    owner: User,
    session: AsyncSession,
) -> Credential:
    credential = await session.scalar(
        select(Credential)
        .join(Target, Target.id == Credential.target_id)
        .join(Project, Project.id == Target.project_id)
        .where(
            Credential.id == credential_id,
            Credential.target_id == target_id,
            Project.owner_id == owner.id,
        )
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    return credential


@router.post(
    "/targets/{target_id}/credentials",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_credential(
    target_id: int,
    payload: CredentialCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CredentialResponse:
    # Ownership is checked through the target's parent project.
    target = await session.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    await get_owned_project(target.project_id, current_user, session)

    credential = Credential(
        target_id=target_id,
        identity_name=payload.identity_name,
        auth_type=payload.auth_type,
        encrypted_value=encrypt_value(payload.value),
    )
    session.add(credential)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity already exists for this target",
        ) from None
    await session.refresh(credential)
    return _to_response(credential)


@router.get(
    "/targets/{target_id}/credentials",
    response_model=list[CredentialResponse],
)
async def list_credentials(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CredentialResponse]:
    target = await session.scalar(select(Target).where(Target.id == target_id))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )
    await get_owned_project(target.project_id, current_user, session)

    credentials = await session.scalars(
        select(Credential)
        .where(Credential.target_id == target_id)
        .order_by(Credential.id)
    )
    return [_to_response(credential) for credential in credentials]


@router.delete(
    "/targets/{target_id}/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_credential(
    target_id: int,
    credential_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    credential = await _get_owned_credential(
        target_id, credential_id, current_user, session
    )
    await session.delete(credential)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
