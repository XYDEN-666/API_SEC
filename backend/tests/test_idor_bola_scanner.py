"""IDOR/BOLA multi-identity replay scanner tests."""

import asyncio
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.crypto import encrypt_value
from app.models import Credential, Evidence, Scan, Target
from app.scanners.idor_bola import IDORScanner
from app.services.orchestrator import ScanOrchestrator
from tests.scanner_harness import run_scanner_against_target

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


def _credential(identity: str, secret: str) -> Credential:
    return Credential(
        target_id=1,
        identity_name=identity,
        auth_type="api_key",
        encrypted_value=encrypt_value(secret),
    )


def test_replays_one_request_per_identity_and_captures_both(
    http_idor_target,
) -> None:
    base_url, hits = http_idor_target()
    admin = _credential("ci-admin", "admin-secret")
    deploy = _credential("deploy", "other-secret")

    scanner = IDORScanner()
    scanner.credentials = [admin, deploy]

    findings = asyncio.run(
        run_scanner_against_target(
            scanner, base_url, path="/users/{user_id}"
        )
    )

    # Exactly two requests to the same object identifier, one per identity.
    assert len(hits) == 2
    assert [path for path, _ in hits] == ["/users/1", "/users/1"]
    assert {api_key for _, api_key in hits} == {"admin-secret", "other-secret"}

    # Both responses are captured in the finding evidence.
    assert len(findings) == 1
    evidence = findings[0].evidence
    assert "ci-admin -> 200" in evidence
    assert "deploy -> 403" in evidence
    assert findings[0].owasp_category == "api1:2023"


def test_endpoint_without_object_identifier_is_skipped(
    http_target,
) -> None:
    scanner = IDORScanner()
    scanner.credentials = [_credential("ci-admin", "admin-secret")]

    findings = asyncio.run(
        run_scanner_against_target(scanner, http_target, path="/")
    )
    assert findings == []


def test_orchestrator_captures_replays_in_evidence(
    client, http_idor_target, unique_email
) -> None:
    base_url, _ = http_idor_target()
    _, token = _register(client, _email("owner"))

    project = client.post(
        "/projects", json={"name": "IDOR Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "IDOR API", "base_url": base_url},
        headers=_auth(token),
    )
    assert target.status_code == 201
    target_id = target.json()["id"]

    spec = {
        "openapi": "3.0.3",
        "info": {"title": "IDOR API", "version": "1.0.0"},
        "paths": {
            "/users/{user_id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
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

    for identity, secret in (
        ("ci-admin", "admin-secret"),
        ("deploy", "other-secret"),
    ):
        created = client.post(
            f"/targets/{target_id}/credentials",
            json={
                "identity_name": identity,
                "auth_type": "api_key",
                "value": secret,
            },
            headers=_auth(token),
        )
        assert created.status_code == 201

    async def _run() -> None:
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            async with AsyncSession(bind=engine) as session:
                target_obj = await session.get(Target, target_id)
                assert target_obj is not None
                result = await ScanOrchestrator([IDORScanner()]).run_scan(
                    target_obj, session
                )
                assert len(result.findings) == 1
                assert "ci-admin -> 200" in result.findings[0].evidence
                assert "deploy -> 403" in result.findings[0].evidence

                scan = await session.get(Scan, result.scan_id)
                assert scan is not None
                evidence = (
                    await session.scalars(
                        select(Evidence).where(
                            Evidence.scan_id == scan.id
                        )
                    )
                ).all()
                assert len(evidence) == 1
                response_data = json.loads(evidence[0].response_data or "{}")
                assert "ci-admin -> 200" in response_data["summary"]
                assert "deploy -> 403" in response_data["summary"]
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_lower_privileged_identity_receives_same_private_object(
    http_idor_target,
) -> None:
    base_url, _ = http_idor_target(mode="bola")
    admin = _credential("admin", "admin-secret")
    intruder = _credential("intruder", "other-secret")

    scanner = IDORScanner()
    scanner.credentials = [admin, intruder]

    findings = asyncio.run(
        run_scanner_against_target(
            scanner, base_url, path="/users/{user_id}"
        )
    )

    # Same 2xx status + overlapping sensitive field (email) -> finding.
    assert len(findings) == 1
    finding = findings[0]
    assert finding.title == "Access-control anomaly detected (IDOR/BOLA)"
    assert "email" in finding.evidence
    assert finding.confidence.value == "high"


def test_properly_isolated_fixture_produces_no_finding(
    http_idor_target,
) -> None:
    base_url, _ = http_idor_target(mode="isolated")
    admin = _credential("admin", "admin-secret")
    intruder = _credential("intruder", "other-secret")

    scanner = IDORScanner()
    scanner.credentials = [admin, intruder]

    findings = asyncio.run(
        run_scanner_against_target(
            scanner, base_url, path="/users/{user_id}"
        )
    )
    assert findings == []


def test_only_noisy_field_matching_does_not_false_positive(
    http_idor_target,
) -> None:
    base_url, _ = http_idor_target(mode="noisy")
    admin = _credential("admin", "admin-secret")
    intruder = _credential("intruder", "other-secret")

    scanner = IDORScanner()
    scanner.credentials = [admin, intruder]

    findings = asyncio.run(
        run_scanner_against_target(
            scanner, base_url, path="/users/{user_id}"
        )
    )
    assert findings == []


def test_ignore_list_is_configurable(http_idor_target) -> None:
    """With the ignore list disabled and a noisy field treated as sensitive,
    the same fixture DOES produce a finding — proving exclusion is the cause."""
    base_url, _ = http_idor_target(mode="noisy")
    admin = _credential("admin", "admin-secret")
    intruder = _credential("intruder", "other-secret")

    scanner = IDORScanner()
    scanner.credentials = [admin, intruder]
    scanner.ignore_fields = set()
    scanner.sensitive_fields = {"email", "created_at"}

    findings = asyncio.run(
        run_scanner_against_target(
            scanner, base_url, path="/users/{user_id}"
        )
    )
    assert len(findings) == 1
    assert "created_at" in findings[0].evidence
