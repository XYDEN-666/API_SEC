"""Findings persistence tests (Task 10.1)."""

import asyncio
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Evidence, Finding, Scan, Target
from app.scanners.base import BaseScanner, Confidence, Finding as ScannerFinding, Severity
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


class TwoFindingScanner(BaseScanner):
    name = "two_finding"
    description = "Returns exactly two findings per endpoint."

    async def scan(self, target, endpoint, credentials):
        return [
            ScannerFinding(
                title="First finding",
                description="Description one.",
                severity=Severity.LOW,
                evidence="evidence-one",
                owasp_category="api5:2023",
                confidence=Confidence.HIGH,
            ),
            ScannerFinding(
                title="Second finding",
                description="Description two.",
                severity=Severity.MEDIUM,
                evidence="evidence-two",
                owasp_category="api5:2023",
                confidence=Confidence.MEDIUM,
            ),
        ]


def test_scan_persists_raw_scanner_findings(client, unique_email) -> None:
    _, token = _register(client, _email("owner"))
    project = client.post(
        "/projects", json={"name": "Findings Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "http://127.0.0.1:9"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    target_id = target.json()["id"]

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
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([TwoFindingScanner()]).run_scan(
                    target_obj, session
                )
                assert len(result.findings) == 2

                findings = list(
                    await session.scalars(
                        select(Finding).where(
                            Finding.scan_id == result.scan_id
                        )
                    )
                )
                assert len(findings) == 2
                for row in findings:
                    assert row.scan_id == result.scan_id
                    assert row.title
                    assert row.description
                    assert row.severity in {"low", "medium"}
                    assert row.endpoint == "http://127.0.0.1:9/health"
                    assert row.owasp_category == "api5:2023"
                    assert row.confidence in {"high", "medium"}
                    assert row.created_at is not None
                    # Each finding links back to its evidence row.
                    evidence = await session.get(Evidence, row.evidence_id)
                    assert evidence is not None
                    assert evidence.scanner_name == "two_finding"

                scan = await session.get(Scan, result.scan_id)
                assert scan is not None
                assert scan.status == "completed"
        finally:
            await engine.dispose()

    asyncio.run(_run())
