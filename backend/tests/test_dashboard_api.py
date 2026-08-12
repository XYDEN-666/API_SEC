"""Dashboard aggregation API tests (Task 13.1)."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import Finding, Project, Scan, Target

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


async def _seed_user(
    user_id: int,
    spec: list[tuple[str, list[tuple[str, str, list[tuple[str, str, list[tuple[str, str, str]]]]]]]],
) -> dict[str, int]:
    """Insert projects/targets/scans/findings directly; return scan ids by label.

    ``spec`` structure: (project_name, [(target_name, base_url,
    [(scan_label, status, [(severity, owasp_category, title), ...]), ...]), ...])
    """
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    scan_ids: dict[str, int] = {}
    try:
        async with AsyncSession(bind=engine) as session:
            for project_name, targets in spec:
                project = Project(name=project_name, owner_id=user_id)
                session.add(project)
                await session.flush()
                for target_name, base_url, scans in targets:
                    target = Target(
                        project_id=project.id,
                        name=target_name,
                        base_url=base_url,
                    )
                    session.add(target)
                    await session.flush()
                    for scan_label, status, findings in scans:
                        scan = Scan(
                            target_id=target.id,
                            status=status,
                            finished_at=datetime.now(timezone.utc),
                        )
                        session.add(scan)
                        await session.flush()
                        scan_ids[scan_label] = scan.id
                        for severity, category, title in findings:
                            session.add(
                                Finding(
                                    scan_id=scan.id,
                                    title=title,
                                    description=f"{title} - seeded finding",
                                    severity=severity,
                                    endpoint=f"{base_url}/probe",
                                    owasp_category=category,
                                    confidence="high",
                                )
                            )
            await session.commit()
    finally:
        await engine.dispose()
    return scan_ids


def test_dashboard_summary_matches_seeded_db_for_owner(client) -> None:
    user_a_id, token_a = _register(client, _email("a"))
    user_b_id, _token_b = _register(client, _email("b"))

    spec_a = [
        (
            "Project A1",
            [
                (
                    "API One",
                    "http://one.example",
                    [
                        (
                            "s1",
                            "completed",
                            [
                                ("critical", "api1:2023", "IDOR on users"),
                                ("critical", "api1:2023", "IDOR on orders"),
                                ("medium", "api2:2023", "JWT missing exp"),
                            ],
                        ),
                        (
                            "s2",
                            "completed_with_errors",
                            [
                                ("high", "api8:2023", "Missing HSTS"),
                                ("info", "api9:2023", "Server banner"),
                            ],
                        ),
                    ],
                ),
                (
                    "API Two",
                    "http://two.example",
                    [
                        (
                            "s3",
                            "completed",
                            [
                                ("medium", "api2:2023", "JWT alg none"),
                                ("low", "api8:2023", "Verbose errors"),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        (
            "Project A2",
            [
                (
                    "API Three",
                    "http://three.example",
                    [
                        (
                            "s4",
                            "completed",
                            [("high", "api10:2023", "SQLi indicator")],
                        ),
                    ],
                ),
            ],
        ),
    ]
    ids_a = asyncio.run(_seed_user(user_a_id, spec_a))
    ids_b = asyncio.run(
        _seed_user(
            user_b_id,
            [
                (
                    "Project B1",
                    [
                        (
                            "API B",
                            "http://b.example",
                            [
                                (
                                    "s5",
                                    "completed",
                                    [("high", "api8:2023", "Missing X-Frame-Options")],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )

    response = client.get("/dashboard/summary", headers=_auth(token_a))
    assert response.status_code == 200
    body = response.json()

    # Counts must match the seeded data exactly.
    assert body["total_projects"] == 2
    assert body["total_targets"] == 3
    assert body["total_scans"] == 4
    assert body["total_findings"] == 8
    assert body["findings_by_severity"] == {
        "critical": 2,
        "high": 2,
        "medium": 2,
        "low": 1,
        "info": 1,
    }
    assert body["findings_by_category"] == {
        "api1:2023": 2,
        "api2:2023": 2,
        "api8:2023": 2,
        "api9:2023": 1,
        "api10:2023": 1,
    }

    # Five most recent scans, newest first, with target, status and top finding.
    assert [scan["id"] for scan in body["recent_scans"]] == [
        ids_a["s4"],
        ids_a["s3"],
        ids_a["s2"],
        ids_a["s1"],
    ]
    expected_recent = [
        ("API Three", "completed", "SQLi indicator", "high"),
        ("API Two", "completed", "JWT alg none", "medium"),
        ("API One", "completed_with_errors", "Missing HSTS", "high"),
        ("API One", "completed", "IDOR on users", "critical"),
    ]
    for scan, (target_name, status, top_title, top_severity) in zip(
        body["recent_scans"], expected_recent
    ):
        assert scan["target_name"] == target_name
        assert scan["status"] == status
        assert scan["top_finding"] == {
            "title": top_title,
            "severity": top_severity,
        }
        assert scan["started_at"] is not None
        assert scan["finished_at"] is not None


def test_dashboard_summary_is_isolated_per_user(client) -> None:
    user_a_id, token_a = _register(client, _email("a"))
    user_b_id, token_b = _register(client, _email("b"))

    asyncio.run(
        _seed_user(
            user_a_id,
            [
                (
                    "Project A1",
                    [
                        (
                            "API A",
                            "http://a.example",
                            [
                                (
                                    "s1",
                                    "completed",
                                    [
                                        ("critical", "api1:2023", "A critical"),
                                        ("low", "api8:2023", "A low"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )
    ids_b = asyncio.run(
        _seed_user(
            user_b_id,
            [
                (
                    "Project B1",
                    [
                        (
                            "API B",
                            "http://b.example",
                            [
                                (
                                    "s2",
                                    "completed",
                                    [("high", "api8:2023", "B high")],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )

    # User A sees only their own data.
    a_body = client.get("/dashboard/summary", headers=_auth(token_a)).json()
    assert a_body["total_projects"] == 1
    assert a_body["total_targets"] == 1
    assert a_body["total_scans"] == 1
    assert a_body["total_findings"] == 2
    assert a_body["findings_by_severity"] == {
        "critical": 1,
        "high": 0,
        "medium": 0,
        "low": 1,
        "info": 0,
    }
    assert a_body["findings_by_category"] == {
        "api1:2023": 1,
        "api8:2023": 1,
    }

    # User B gets a completely different, correctly-scoped result: none of
    # user A's projects/targets/scans/findings may appear.
    b_body = client.get("/dashboard/summary", headers=_auth(token_b)).json()
    assert b_body["total_projects"] == 1
    assert b_body["total_targets"] == 1
    assert b_body["total_scans"] == 1
    assert b_body["total_findings"] == 1
    assert b_body["findings_by_severity"] == {
        "critical": 0,
        "high": 1,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    assert b_body["findings_by_category"] == {"api8:2023": 1}
    assert len(b_body["recent_scans"]) == 1
    assert b_body["recent_scans"][0]["id"] == ids_b["s2"]
    assert b_body["recent_scans"][0]["target_name"] == "API B"
    assert b_body["recent_scans"][0]["top_finding"] == {
        "title": "B high",
        "severity": "high",
    }


def test_dashboard_summary_requires_auth(client) -> None:
    assert client.get("/dashboard/summary").status_code == 401
