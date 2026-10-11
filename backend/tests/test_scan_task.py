"""Celery scan-task terminal-state tests.

The worker owns the "running" -> terminal transition, so a failing run must
leave the scan ``failed`` instead of stuck ``running`` forever.
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Scan
from app.services.orchestrator import ScanOrchestrator
from app.tasks.scans import run_scan as run_scan_task

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
        "/projects", json={"name": "Scan Task Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    return target.json()["id"]


def _create_queued_scan(target_id: int) -> int:
    async def _run() -> int:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                scan = Scan(target_id=target_id, status="queued")
                session.add(scan)
                await session.commit()
                await session.refresh(scan)
                return scan.id
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _scan_state(scan_id: int) -> tuple[str, bool]:
    async def _run() -> tuple[str, bool]:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                scan = await session.get(Scan, scan_id)
                assert scan is not None
                return scan.status, scan.finished_at is not None
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def test_worker_marks_scan_failed_when_orchestrator_raises(
    client, unique_email, monkeypatch
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    scan_id = _create_queued_scan(target_id)

    async def _explode(self, target, session, scan_id=None):
        raise RuntimeError("orchestrator exploded")

    monkeypatch.setattr(ScanOrchestrator, "run_scan", _explode)

    outcome = run_scan_task(scan_id, target_id)

    assert outcome["status"] == "failed"
    assert outcome["scan_db_id"] == scan_id
    assert _scan_state(scan_id) == ("failed", True)


def test_worker_marks_scan_failed_when_target_missing(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    scan_id = _create_queued_scan(target_id)

    outcome = run_scan_task(scan_id, target_id + 999_999)

    assert outcome["status"] == "error"
    assert _scan_state(scan_id) == ("failed", True)
