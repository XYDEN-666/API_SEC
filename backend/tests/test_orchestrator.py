"""ScanOrchestrator tests: plumbing with zero and registered scanners."""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Target
from app.scanners.base import BaseScanner, Confidence, Finding, Severity
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


class EchoScanner(BaseScanner):
    name = "echo"
    description = "Returns a single finding per endpoint."

    async def scan(self, target, endpoint, credentials):
        return [
            Finding(
                title="Echo finding",
                description="Produced by the echo scanner.",
                severity=Severity.INFO,
                evidence=f"{endpoint.method} {endpoint.path}",
                owasp_category="api5:2023",
                confidence=Confidence.HIGH,
            )
        ]


class BrokenScanner(BaseScanner):
    name = "broken"
    description = "Always raises."

    async def scan(self, target, endpoint, credentials):
        raise RuntimeError("boom")


def test_orchestrator_with_zero_scanners_returns_empty_result(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None
                result = await ScanOrchestrator().run_scan(target, session)
                assert result.findings == []
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_orchestrator_collects_findings_and_survives_broken_scanner(
    client, unique_email
) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    # Give the target one endpoint so scanners have something to run against.
    import json

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "API", "version": "1.0.0"},
        "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}},
    }
    upload = client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "openapi.json",
                json.dumps(spec).encode(),
                "application/json",
            )
        },
        headers=_auth(token),
    )
    assert upload.status_code == 200

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None
                result = await ScanOrchestrator(
                    [EchoScanner(), BrokenScanner()]
                ).run_scan(target, session)
                # Echo produced one finding per endpoint; Broken was logged
                # and skipped without aborting the run.
                assert len(result.findings) == 1
                assert result.findings[0].title == "Echo finding"
                assert result.findings[0].evidence == "GET /health"
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_register_adds_scanner(client, unique_email) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    import json

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "API", "version": "1.0.0"},
        "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}},
    }
    upload = client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "openapi.json",
                json.dumps(spec).encode(),
                "application/json",
            )
        },
        headers=_auth(token),
    )
    assert upload.status_code == 200

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None
                orchestrator = ScanOrchestrator()
                orchestrator.register(EchoScanner())
                result = await orchestrator.run_scan(target, session)
                assert len(result.findings) == 1
        finally:
            await engine.dispose()

    asyncio.run(_run())
