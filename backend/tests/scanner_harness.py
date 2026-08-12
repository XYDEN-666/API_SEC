"""Reusable scanner smoke-test harness.

Points a scanner at a real (in-process) HTTP fixture target, runs its
``scan()``, and asserts the returned findings match the standard
:class:`~app.scanners.base.Finding` shape.

Example usage in a test:

    from tests.scanner_harness import http_target, run_scanner_against_target

    def test_my_scanner(http_target):
        findings = asyncio.run(
            run_scanner_against_target(MyScanner(), http_target)
        )
        assert findings  # or assert specific finding fields
"""

import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from app.models import Endpoint, Target
from app.scanners.base import Confidence, Finding, Severity

REQUIRED_FIELDS = (
    "title",
    "description",
    "severity",
    "evidence",
    "owasp_category",
    "confidence",
)


def assert_findings_shape(findings: list[Finding]) -> None:
    """Assert every finding carries the standard, valid fields."""
    for finding in findings:
        for field in REQUIRED_FIELDS:
            assert hasattr(finding, field), f"finding missing {field!r}"
        assert isinstance(finding.title, str) and finding.title
        assert isinstance(finding.description, str) and finding.description
        assert isinstance(finding.evidence, str) and finding.evidence
        assert isinstance(finding.owasp_category, str) and finding.owasp_category
        assert isinstance(finding.severity, Severity)
        assert isinstance(finding.confidence, Confidence)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(app: FastAPI) -> tuple[str, uvicorn.Server, threading.Thread]:
    """Start ``app`` on a random local port; return (base_url, server, thread)."""
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("HTTP fixture target failed to start")
        time.sleep(0.01)
    return f"http://127.0.0.1:{port}", server, thread


@pytest.fixture
def http_target():
    """Start a tiny HTTP API on a random local port and yield its base URL."""
    app = FastAPI()

    @app.get("/")
    def root() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    base_url, server, thread = _start_server(app)
    yield base_url

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def http_multi_endpoint_target():
    """Fixture target with three endpoints that all omit security headers."""
    started: list[tuple[uvicorn.Server, threading.Thread]] = []

    def _start() -> str:
        app = FastAPI()

        @app.get("/a")
        def endpoint_a() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/b")
        def endpoint_b() -> dict[str, bool]:
            return {"ok": True}

        @app.get("/c")
        def endpoint_c() -> dict[str, bool]:
            return {"ok": True}

        base_url, server, thread = _start_server(app)
        started.append((server, thread))
        return base_url

    yield _start

    for server, thread in started:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture
def http_target_factory():
    """Start HTTP targets that return a configurable set of response headers."""
    started: list[tuple[uvicorn.Server, threading.Thread]] = []

    def _start(
        headers: dict[str, str] | None = None,
        allow_methods: list[str] | None = None,
        body: dict | None = None,
    ) -> str:
        app = FastAPI()

        @app.get("/")
        def root(response: Response) -> dict[str, object]:
            for name, value in (headers or {}).items():
                response.headers[name] = value
            return (body or {"ok": True})  # type: ignore[return-value]

        for method in allow_methods or []:
            app.add_api_route(
                "/",
                lambda: {"ok": True},
                methods=[method],
                name=f"extra_{method.lower()}",
            )

        base_url, server, thread = _start_server(app)
        started.append((server, thread))
        return base_url

    yield _start

    for server, thread in started:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture
def http_sqli_target():
    """Fixture target with error-based SQLi behavior on /users/{user_id}
    and /search (query param)."""
    started: list[tuple[uvicorn.Server, threading.Thread]] = []

    def _start(vulnerable: bool) -> str:
        app = FastAPI()

        @app.get("/users/{user_id}")
        def user(user_id: str):
            if vulnerable and "'" in user_id:
                return PlainTextResponse(
                    'psycopg2.errors.SyntaxError: syntax error at or near "\'" '
                    "LINE 1: ... SQLSTATE 42601"
                )
            return {"id": user_id, "ok": True}

        @app.get("/search")
        def search(q: str = ""):
            if vulnerable and "'" in q:
                return PlainTextResponse(
                    "sqlalchemy.exc.ProgrammingError: syntax error near "
                    '"\'" SQLSTATE 42601'
                )
            return {"query": q, "ok": True}

        base_url, server, thread = _start_server(app)
        started.append((server, thread))
        return base_url

    yield _start

    for server, thread in started:
        server.should_exit = True
        thread.join(timeout=10)


@pytest.fixture
def http_idor_target():
    """Fixture target with an object-identifier endpoint that distinguishes
    identities via the X-API-Key header, plus a request log.

    Modes:
    * ``forbidden`` (default): non-admin identities get 403.
    * ``bola``: non-admin identities get 200 with the same private object.
    * ``isolated``: non-admin identities get 200 with their own object.
    * ``noisy``: non-admin identities get 200 with their own object, but the
      timestamp matches the admin's (a noisy field only).
    """
    started: list[tuple[uvicorn.Server, threading.Thread]] = []

    def _start(mode: str = "forbidden") -> tuple[str, list]:
        hits: list[tuple[str, str | None]] = []
        app = FastAPI()

        @app.get("/users/{user_id}")
        def user(user_id: str, request: Request):
            api_key = request.headers.get("x-api-key")
            hits.append((request.url.path, api_key))
            if api_key == "admin-secret":
                if mode == "noisy":
                    return {
                        "id": user_id,
                        "email": "owner@example.com",
                        "created_at": "2026-08-12T00:00:00Z",
                        "request_id": "req-owner",
                        "ok": True,
                    }
                return {
                    "id": user_id,
                    "email": "owner@example.com",
                    "ok": True,
                }
            if mode == "bola":
                return {
                    "id": user_id,
                    "email": "owner@example.com",
                    "ok": True,
                }
            if mode == "isolated":
                return {
                    "id": user_id,
                    "email": "intruder@example.com",
                    "ok": True,
                }
            if mode == "noisy":
                return {
                    "id": user_id,
                    "email": "intruder@example.com",
                    "created_at": "2026-08-12T00:00:00Z",
                    "request_id": "req-intruder",
                    "ok": True,
                }
            return JSONResponse({"error": "forbidden"}, status_code=403)

        base_url, server, thread = _start_server(app)
        started.append((server, thread))
        return base_url, hits

    yield _start

    for server, thread in started:
        server.should_exit = True
        thread.join(timeout=10)


async def run_scanner_against_target(
    scanner,
    base_url: str,
    path: str = "/",
    method: str = "GET",
    credentials=None,
    parameters=None,
) -> list[Finding]:
    """Run ``scanner.scan()`` against the fixture target and validate shape.

    Returns the findings after asserting every one matches the standard
    Finding shape.
    """
    target = Target(
        project_id=1,
        base_url=base_url,
        name="Harness Target",
    )
    endpoint = Endpoint(
        target_id=1,
        path=path,
        method=method,
        parameters=parameters,
    )
    findings = await scanner.scan(target, endpoint, credentials)
    assert_findings_shape(findings)
    return findings
