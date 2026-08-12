"""Target CRUD routes, scoped to the owning project."""

import json
from typing import Annotated

import yaml
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Endpoint, Project, Target, User
from app.routers.projects import get_owned_project
from app.schemas.endpoint import EndpointResponse
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


def _parse_document(text: str) -> dict:
    try:
        spec = json.loads(text)
    except json.JSONDecodeError:
        try:
            spec = yaml.safe_load(text)
        except yaml.YAMLError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be valid JSON or YAML",
            ) from None
    if not isinstance(spec, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAPI document must be a JSON or YAML object",
        )
    return spec


def _validate_openapi3(spec: dict) -> None:
    if "swagger" in spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Swagger 2.0 import is not supported (Deferred scope). "
                "Provide an OpenAPI 3.x document."
            ),
        )
    if "openapi" not in spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not an OpenAPI document: missing 'openapi' field",
        )

    version = spec["openapi"]
    if not isinstance(version, str) or not version.startswith("3."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported OpenAPI version {version!r}; "
                "only 3.x documents are supported"
            ),
        )
    if not isinstance(spec.get("info"), dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAPI document: missing 'info' object",
        )
    if not isinstance(spec.get("paths"), dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAPI document: missing 'paths' object",
        )


_HTTP_METHODS = {
    "get",
    "put",
    "post",
    "delete",
    "options",
    "head",
    "patch",
    "trace",
}


def _merge_parameters(*groups: list) -> list:
    """Concatenate parameter groups, deduplicating by (name, in)."""
    seen: set[tuple] = set()
    merged: list = []
    for group in groups:
        for param in group:
            if not isinstance(param, dict):
                continue
            key = (param.get("name"), param.get("in"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(param)
    return merged


def _extract_endpoints(spec: dict) -> list[dict]:
    """Flatten an OpenAPI spec into one row per path+method operation."""
    endpoints: list[dict] = []
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = (
            path_item.get("parameters")
            if isinstance(path_item.get("parameters"), list)
            else []
        )
        for method in _HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            operation_parameters = (
                operation.get("parameters")
                if isinstance(operation.get("parameters"), list)
                else []
            )
            merged = _merge_parameters(path_parameters, operation_parameters)
            endpoints.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "parameters": merged or None,
                }
            )
    return endpoints


@router.post("/targets/{target_id}/import-openapi")
async def import_openapi(
    target_id: int,
    file: Annotated[UploadFile, File(...)],
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    """Parse and validate an OpenAPI 3.x document (JSON or YAML) upload."""
    target = await _get_owned_target(target_id, current_user, session)

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid JSON or YAML",
        ) from None

    spec = _parse_document(text)
    _validate_openapi3(spec)
    endpoints = _extract_endpoints(spec)

    # Replace the target's extracted endpoints on every import.
    await session.execute(
        delete(Endpoint).where(Endpoint.target_id == target.id)
    )
    for endpoint in endpoints:
        session.add(
            Endpoint(
                target_id=target.id,
                path=endpoint["path"],
                method=endpoint["method"],
                parameters=endpoint["parameters"],
            )
        )
    await session.commit()

    info = spec["info"]
    return {
        "message": "OpenAPI 3.x document imported successfully",
        "openapi": spec["openapi"],
        "title": info.get("title"),
        "version": info.get("version"),
        "paths_count": len(spec["paths"]),
        "endpoints_count": len(endpoints),
    }


@router.get("/targets/{target_id}/endpoints", response_model=list[EndpointResponse])
async def list_endpoints(
    target_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Endpoint]:
    await _get_owned_target(target_id, current_user, session)
    endpoints = await session.scalars(
        select(Endpoint)
        .where(Endpoint.target_id == target_id)
        .order_by(Endpoint.id)
    )
    return list(endpoints)
