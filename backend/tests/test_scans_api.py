"""Scan trigger endpoint tests."""

import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Target
from app.services.orchestrator import ScanOrchestrator

PASSWORD = "CorrectHorse42!"


def _email(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex}@example.com"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str) -> tuple[int, str]:
    register = client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200
    return register.json()["id"], login.json()["access_token"]


def _create_project_with_target(client, token: str) -> int:
    project = client.post(
        "/projects", json={"name": "Scan Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    return target.json()["id"]


def test_start_scan_returns_scan_id_immediately(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    started = client.post(
        f"/targets/{target_id}/scans", headers=_auth(token)
    )

    assert started.status_code == 202
    body = started.json()
    assert body["status"] == "queued"
    assert len(body["scan_id"]) > 20  # celery task id (uuid)


def test_start_scan_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_project_with_target(client, owner_token)

    assert (
        client.post(
            f"/targets/{target_id}/scans", headers=_auth(other_token)
        ).status_code
        == 404
    )
    assert client.post(f"/targets/{target_id}/scans").status_code == 401


def _create_scan(target_id: int) -> int:
    """Create a completed scan row directly via the orchestrator."""

    async def _run() -> int:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None
                result = await ScanOrchestrator([]).run_scan(target, session)
                return result.scan_id
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_list_target_scans_newest_first(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    first = _create_scan(target_id)
    second = _create_scan(target_id)

    response = client.get(f"/targets/{target_id}/scans", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [second, first]
    for item in body:
        assert item["target_id"] == target_id
        assert item["status"] == "completed"
        assert item["started_at"]
        assert item["finished_at"]


def test_list_target_scans_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_project_with_target(client, owner_token)
    _create_scan(target_id)

    assert client.get(f"/targets/{target_id}/scans").status_code == 401
    assert (
        client.get(
            f"/targets/{target_id}/scans", headers=_auth(other_token)
        ).status_code
        == 404
    )
    assert (
        client.get("/targets/999999/scans", headers=_auth(owner_token)).status_code
        == 404
    )
