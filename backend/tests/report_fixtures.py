"""Shared fixtures for report tests (HTML/PDF/JSON)."""

import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Target
from app.scanners.base import (
    BaseScanner,
    Confidence,
    Finding as ScannerFinding,
    Severity,
)
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


def create_target_with_endpoint(
    client, token: str, base_url: str = "http://127.0.0.1:9"
) -> int:
    """Create a project, target and one imported endpoint; return target id."""
    project = client.post(
        "/projects", json={"name": "Report Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "Report API", "base_url": base_url},
        headers=_auth(token),
    )
    assert target.status_code == 201
    target_id = target.json()["id"]

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Report API", "version": "1.0.0"},
        "paths": {
            "/health": {"get": {"responses": {"200": {"description": "ok"}}}}
        },
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
    return target_id


def run_scan(target_id: int, scanner) -> int:
    """Run an orchestrator scan directly; return the persisted scan id."""

    async def _run() -> int:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([scanner]).run_scan(
                    target_obj, session
                )
                return result.scan_id
        finally:
            await engine.dispose()

    return asyncio.run(_run())


class ReportScanner(BaseScanner):
    """Emits findings across severities and OWASP categories."""

    name = "report_fixture"
    description = "Produces varied findings for report tests."

    async def scan(self, target, endpoint, credentials):
        return [
            ScannerFinding(
                title="Missing HSTS header",
                description="The endpoint does not send Strict-Transport-Security.",
                severity=Severity.HIGH,
                evidence="request-1: header absent",
                owasp_category="api8:2023",
                confidence=Confidence.HIGH,
            ),
            ScannerFinding(
                title="JWT missing exp claim",
                description="A returned token lacks an expiration claim.",
                severity=Severity.MEDIUM,
                evidence="request-2: token observed",
                owasp_category="api2:2023",
                confidence=Confidence.MEDIUM,
            ),
            ScannerFinding(
                title="Informational note",
                description="An informational observation.",
                severity=Severity.INFO,
                evidence="request-3",
                owasp_category="api2:2023",
                confidence=Confidence.LOW,
            ),
        ]
