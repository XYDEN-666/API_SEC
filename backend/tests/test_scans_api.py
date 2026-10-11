"""Scan trigger endpoint tests."""

import asyncio
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Scan, Target
from app.routers import scans as scans_router
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


class _RecordingTask:
    """Stand-in for the Celery task: records the enqueue, runs nothing."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def delay(self, scan_id: int, target_id: int) -> None:
        self.calls.append((scan_id, target_id))


def _load_scan(scan_id: int) -> Scan | None:
    """Read a scan row on its own engine (TestClient's loop is closed)."""

    async def _run() -> Scan | None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                return await session.get(Scan, scan_id)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _scans_for_target(target_id: int) -> list[Scan]:
    async def _run() -> list[Scan]:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                return list(
                    await session.scalars(
                        select(Scan)
                        .where(Scan.target_id == target_id)
                        .order_by(Scan.id.desc())
                    )
                )
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_start_scan_returns_real_scan_id_immediately(
    client, monkeypatch
) -> None:
    """The response carries the DB scan id, and the row exists before the
    worker is enqueued so the UI can poll that exact scan."""
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    task = _RecordingTask()
    monkeypatch.setattr(scans_router, "run_scan", task)

    started = client.post(
        f"/targets/{target_id}/scans", headers=_auth(token)
    )

    assert started.status_code == 202
    body = started.json()
    assert body["status"] == "queued"
    assert isinstance(body["scan_id"], int)

    # A real, pollable row was created for this target...
    scan = _load_scan(body["scan_id"])
    assert scan is not None
    assert scan.target_id == target_id
    assert scan.status == "queued"
    assert scan.finished_at is None

    # ...and the worker was handed that same id, not a Celery task uuid.
    assert task.calls == [(body["scan_id"], target_id)]


def test_start_scan_marks_scan_failed_when_broker_unreachable(
    client, monkeypatch
) -> None:
    """A scan that cannot be queued must not be left stuck as "queued"."""
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    class _BrokenTask:
        def delay(self, scan_id: int, target_id: int) -> None:
            raise RuntimeError("broker down")

    monkeypatch.setattr(scans_router, "run_scan", _BrokenTask())

    response = client.post(f"/targets/{target_id}/scans", headers=_auth(token))

    assert response.status_code == 503
    scans = _scans_for_target(target_id)
    assert len(scans) == 1
    assert scans[0].status == "failed"
    assert scans[0].finished_at is not None


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
