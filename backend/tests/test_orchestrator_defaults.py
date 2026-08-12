"""Default scanner registration tests (Task 6.4)."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Evidence, Scan, Target
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


def _create_target(client, token: str, base_url: str) -> int:
    project = client.post(
        "/projects", json={"name": "Defaults Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "Fixture API", "base_url": base_url},
        headers=_auth(token),
    )
    assert target.status_code == 201
    target_id = target.json()["id"]

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Fixture API", "version": "1.0.0"},
        "paths": {
            "/": {"get": {"responses": {"200": {"description": "ok"}}}}
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


def test_default_scanners_all_report_findings(
    client, http_target_factory, unique_email
) -> None:
    """One fixture with misconfigs in all three areas yields findings from
    every default scanner."""
    base_url = http_target_factory(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            # All security headers intentionally missing.
        },
        allow_methods=["TRACE"],
    )
    _, token = _register(client, _email("owner"))
    target_id = _create_target(client, token, base_url)

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None

                result = await ScanOrchestrator().run_scan(target, session)

                titles = {finding.title for finding in result.findings}
                # Headers scanner.
                assert any(
                    "Strict-Transport-Security" in title
                    or "X-Content-Type-Options" in title
                    or "Content-Security-Policy" in title
                    or "X-Frame-Options" in title
                    for title in titles
                ), f"headers findings missing from {titles}"
                # CORS scanner.
                assert any("CORS" in title for title in titles), (
                    f"cors findings missing from {titles}"
                )
                # HTTP methods scanner.
                assert any(
                    "method enabled" in title
                    or "advertises dangerous methods" in title
                    for title in titles
                ), f"http methods findings missing from {titles}"

                # Evidence rows were recorded for all three default scanners.
                scan = await session.get(Scan, result.scan_id)
                assert scan is not None
                evidence = (
                    await session.scalars(
                        select(Evidence).where(Evidence.scan_id == scan.id)
                    )
                ).all()
                scanner_names = {row.scanner_name for row in evidence}
                assert {"headers", "cors", "http_methods"} <= scanner_names, (
                    f"expected all default scanners, got {scanner_names}"
                )
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_jwt_finding_alongside_week6_findings(
    client, http_target_factory, unique_email
) -> None:
    """A bad JWT produces its finding alongside the other default scanners'."""
    bad_token = jwt.encode(
        {"sub": "1"},  # no exp on purpose
        "some-secret",
        algorithm="HS256",
    )
    base_url = http_target_factory(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
        allow_methods=["TRACE"],
        body={"token": bad_token},
    )
    _, token = _register(client, _email("owner"))
    target_id = _create_target(client, token, base_url)

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target = await session.get(Target, target_id)
                assert target is not None

                result = await ScanOrchestrator().run_scan(target, session)
                titles = {finding.title for finding in result.findings}

                # JWT scanner finding.
                assert "JWT missing exp claim" in titles
                # Week 6 scanner findings.
                assert any(
                    "Strict-Transport-Security" in title
                    or "Content-Security-Policy" in title
                    for title in titles
                )
                assert any("CORS" in title for title in titles)
                assert any("method enabled" in title for title in titles)

                scan = await session.get(Scan, result.scan_id)
                assert scan is not None
                evidence = (
                    await session.scalars(
                        select(Evidence).where(Evidence.scan_id == scan.id)
                    )
                ).all()
                scanner_names = {row.scanner_name for row in evidence}
                assert {"headers", "cors", "http_methods", "jwt"} <= scanner_names
        finally:
            await engine.dispose()

    asyncio.run(_run())
