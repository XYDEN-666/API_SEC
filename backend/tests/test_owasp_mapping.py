"""OWASP API Top 10 mapping tests (Task 10.2)."""

import asyncio
import json
import re
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Finding, Target
from app.scanners.base import BaseScanner, Confidence, Finding as ScannerFinding, Severity
from app.services.orchestrator import ScanOrchestrator, _DEFAULT_SCANNER_CLASSES
from app.services.owasp_mapping import (
    OWASP_API_TOP_10_2023,
    category_for_scanner,
)

PASSWORD = "CorrectHorse42!"
_CATEGORY_RE = re.compile(r"api\d+:2023")


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


def test_every_default_scanner_has_a_registered_category() -> None:
    """All six default scanners resolve to a non-empty apiX:2023 category."""
    names = {scanner_cls.name for scanner_cls in _DEFAULT_SCANNER_CLASSES}
    assert names == set(OWASP_API_TOP_10_2023)
    for name in names:
        category = category_for_scanner(name)
        assert category
        assert _CATEGORY_RE.fullmatch(category), category


def test_expected_category_mappings() -> None:
    assert category_for_scanner("idor_bola") == "api1:2023"
    assert category_for_scanner("jwt") == "api2:2023"
    assert category_for_scanner("headers") == "api8:2023"
    assert category_for_scanner("cors") == "api8:2023"
    assert category_for_scanner("http_methods") == "api8:2023"
    assert category_for_scanner("sqli_indicators") == "api10:2023"


def test_unregistered_scanner_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="No OWASP API Top 10 category"):
        category_for_scanner("no_such_scanner")


class CategorylessScanner(BaseScanner):
    """Scanner that returns findings without an OWASP category on purpose."""

    name = "headers"
    description = "Returns a finding with an empty owasp_category."

    async def scan(self, target, endpoint, credentials):
        return [
            ScannerFinding(
                title="Uncategorized issue",
                description="Scanner omitted the category.",
                severity=Severity.LOW,
                evidence="no category supplied",
                owasp_category="",
                confidence=Confidence.HIGH,
            )
        ]


def test_persisted_finding_never_has_null_or_empty_category(
    client, unique_email
) -> None:
    """The orchestrator fills in the registered category when a scanner
    returns an empty one, so persisted findings always have a category."""
    _, token = _register(client, _email("owner"))
    project = client.post(
        "/projects", json={"name": "Mapping Project"}, headers=_auth(token)
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
                result = await ScanOrchestrator([CategorylessScanner()]).run_scan(
                    target_obj, session
                )
                rows = list(
                    await session.scalars(
                        select(Finding).where(Finding.scan_id == result.scan_id)
                    )
                )
                assert len(rows) == 1
                row = rows[0]
                # The scanner returned an empty category; the orchestrator
                # must have substituted the registered one for "headers".
                assert row.owasp_category == category_for_scanner("headers")
                assert row.owasp_category == "api8:2023"
        finally:
            await engine.dispose()

    asyncio.run(_run())
