"""Finding deduplication tests (Task 10.4)."""

import asyncio
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Finding, Target
from app.scanners.base import (
    BaseScanner,
    Confidence,
    Finding as ScannerFinding,
    Severity,
)
from app.scanners.headers import HeaderScanner
from app.services.deduplication import (
    FindingDeduplicator,
    finding_dedup_key,
    normalize_finding_signature,
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


def _create_target(
    client, token: str, base_url: str, paths: list[str]
) -> int:
    project = client.post(
        "/projects", json={"name": "Dedup Project"}, headers=_auth(token)
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


def _finding(**overrides) -> ScannerFinding:
    defaults = {
        "title": "Missing X-Frame-Options",
        "description": "Endpoint does not send X-Frame-Options.",
        "severity": Severity.MEDIUM,
        "evidence": "GET /a returned no header",
        "owasp_category": "api8:2023",
        "confidence": Confidence.HIGH,
    }
    defaults.update(overrides)
    return ScannerFinding(**defaults)


def test_signature_normalizes_whitespace_and_case() -> None:
    first = _finding(
        title="  Missing X-FRAME-Options ",
        description="Endpoint does not send X-Frame-Options.",
    )
    second = _finding(
        title="missing x-frame-options",
        description="Endpoint   does not send\nX-Frame-Options.",
    )
    assert normalize_finding_signature(first) == normalize_finding_signature(second)


def test_signature_excludes_evidence() -> None:
    # Same issue observed across two requests: evidence differs, signature
    # must not, otherwise per-request observations would never collapse.
    first = _finding(evidence="request-1: header absent")
    second = _finding(evidence="request-2: captured at 10:00:00")
    assert normalize_finding_signature(first) == normalize_finding_signature(second)


def test_dedup_key_distinguishes_endpoint_scanner_and_scan() -> None:
    finding = _finding()
    key_a = finding_dedup_key(1, "GET /a", "headers", finding)
    key_b = finding_dedup_key(1, "GET /b", "headers", finding)
    key_other_scanner = finding_dedup_key(1, "GET /a", "cors", finding)
    key_other_scan = finding_dedup_key(2, "GET /a", "headers", finding)
    assert key_a != key_b
    assert key_a != key_other_scanner
    assert key_a != key_other_scan


def test_deduplicator_collapses_repeats_keeps_distinct() -> None:
    dedup = FindingDeduplicator(scan_id=7)
    finding = _finding()
    assert dedup.is_duplicate("GET /a", "headers", finding) is False
    assert dedup.is_duplicate("GET /a", "headers", finding) is True
    assert dedup.is_duplicate("GET /b", "headers", finding) is False
    assert dedup.is_duplicate("GET /a", "cors", finding) is False


def test_same_issue_across_endpoints_stays_distinct(
    client, http_multi_endpoint_target, unique_email
) -> None:
    """Three endpoints missing the same header produce three rows, one per
    endpoint -- the endpoint component of the dedup key keeps them apart."""
    base_url = http_multi_endpoint_target()
    _, token = _register(client, _email("owner"))
    target_id = _create_target(client, token, base_url, ["/a", "/b", "/c"])

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([HeaderScanner()]).run_scan(
                    target_obj, session
                )
                rows = list(
                    await session.scalars(
                        select(Finding).where(
                            Finding.scan_id == result.scan_id
                        )
                    )
                )
                # 4 missing security headers x 3 endpoints, none collapsed.
                assert len(rows) == 12
                xfo = [
                    row for row in rows
                    if row.title == "Missing X-Frame-Options"
                ]
                assert len(xfo) == 3
                assert {row.endpoint for row in xfo} == {
                    f"{base_url}{path}" for path in ("/a", "/b", "/c")
                }
        finally:
            await engine.dispose()

    asyncio.run(_run())


class RepeatingScanner(BaseScanner):
    """Reports the same issue once per request, three times."""

    name = "repeating"
    description = "Detects the same issue in every request to an endpoint."

    async def scan(self, target, endpoint, credentials):
        return [
            ScannerFinding(
                title="Repeated issue",
                description="Detected in every request to this endpoint.",
                severity=Severity.MEDIUM,
                evidence=f"request-{i}: observed",
                owasp_category="api8:2023",
                confidence=Confidence.HIGH,
            )
            for i in range(3)
        ]


def test_true_duplicates_on_same_endpoint_collapse(
    client, unique_email
) -> None:
    """The same issue detected across three requests for one endpoint is
    persisted once, and the returned findings list is deduplicated too."""
    _, token = _register(client, _email("owner"))
    target_id = _create_target(
        client, token, "http://127.0.0.1:9", ["/health"]
    )

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([RepeatingScanner()]).run_scan(
                    target_obj, session
                )
                assert len(result.findings) == 1
                rows = list(
                    await session.scalars(
                        select(Finding).where(
                            Finding.scan_id == result.scan_id
                        )
                    )
                )
                assert len(rows) == 1
                assert rows[0].title == "Repeated issue"
        finally:
            await engine.dispose()

    asyncio.run(_run())
