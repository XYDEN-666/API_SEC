"""Findings API tests (Task 10.5)."""

import asyncio
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Scan, Target
from app.scanners.base import (
    BaseScanner,
    Confidence,
    Finding as ScannerFinding,
    Severity,
)
from app.scanners.headers import HeaderScanner
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


def _create_target(
    client, token: str, base_url: str, paths: list[str]
) -> int:
    project = client.post(
        "/projects", json={"name": "Findings API Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": base_url},
        headers=_auth(token),
    )
    assert target.status_code == 201
    target_id = target.json()["id"]

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "API", "version": "1.0.0"},
        "paths": {
            path: {"get": {"responses": {"200": {"description": "ok"}}}}
            for path in paths
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


def _run_scan(target_id: int, scanner) -> int:
    """Run an orchestrator scan directly and return the persisted scan id."""

    async def _run() -> int:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([scanner]).run_scan(
                    target_obj, session
                )
                scan = await session.get(Scan, result.scan_id)
                assert scan is not None
                assert scan.status == "completed"
                return result.scan_id
        finally:
            await engine.dispose()

    return asyncio.run(_run())


class SampleScanner(BaseScanner):
    """Emits the same issue twice per endpoint (simulating two requests)."""

    name = "sample"
    description = "Detects a missing header in every request."

    async def scan(self, target, endpoint, credentials):
        return [
            ScannerFinding(
                title="Missing X-Frame-Options",
                description="Endpoint does not send X-Frame-Options.",
                severity=Severity.MEDIUM,
                evidence=f"request-{i}: header absent",
                owasp_category="api8:2023",
                confidence=Confidence.HIGH,
            )
            for i in range(2)
        ]


def test_findings_api_returns_scored_categorized_deduplicated(
    client, unique_email
) -> None:
    """A completed scan with duplicate emissions per endpoint returns one
    correctly scored and categorized finding per endpoint."""
    _, token = _register(client, _email("owner"))
    target_id = _create_target(
        client, token, "http://127.0.0.1:9", ["/a", "/b", "/c"]
    )
    scan_id = _run_scan(target_id, SampleScanner())

    response = client.get(f"/scans/{scan_id}/findings", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()

    # 2 duplicate emissions per endpoint collapse to 1; 3 endpoints stay 3.
    assert len(body) == 3
    assert {item["endpoint"] for item in body} == {
        f"http://127.0.0.1:9{path}" for path in ("/a", "/b", "/c")
    }
    for item in body:
        assert item["scan_id"] == scan_id
        assert item["title"] == "Missing X-Frame-Options"
        assert item["severity"] == "medium"
        assert item["owasp_category"] == "api8:2023"
        assert item["confidence"] == "high"
        # MEDIUM severity + HIGH confidence -> 6.0 / High.
        assert item["risk_score"] == 6.0
        assert item["risk_label"] == "High"
        assert item["evidence_id"] is not None


def test_findings_api_real_headers_scan_scored_and_categorized(
    client, http_multi_endpoint_target, unique_email
) -> None:
    """A real HeaderScanner scan returns per-endpoint findings with the
    correct category and risk score (MEDIUM+HIGH -> 6.0 / High)."""
    base_url = http_multi_endpoint_target()
    _, token = _register(client, _email("owner"))
    target_id = _create_target(client, token, base_url, ["/a", "/b", "/c"])
    scan_id = _run_scan(target_id, HeaderScanner())

    response = client.get(f"/scans/{scan_id}/findings", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()

    # 4 missing security headers x 3 endpoints; none are duplicates because
    # the endpoint differs.
    assert len(body) == 12
    for item in body:
        assert item["severity"] == "medium"
        assert item["owasp_category"] == "api8:2023"
        assert item["confidence"] == "high"
        assert item["risk_score"] == 6.0
        assert item["risk_label"] == "High"


def test_findings_api_scoped_to_owner_and_requires_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_target(
        client, owner_token, "http://127.0.0.1:9", ["/health"]
    )
    scan_id = _run_scan(target_id, SampleScanner())

    assert client.get(f"/scans/{scan_id}/findings").status_code == 401
    assert (
        client.get(
            f"/scans/{scan_id}/findings", headers=_auth(other_token)
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/scans/999999/findings", headers=_auth(owner_token)
        ).status_code
        == 404
    )
