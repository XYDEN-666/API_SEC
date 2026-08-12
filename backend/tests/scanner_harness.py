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
from fastapi import FastAPI

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

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)


async def run_scanner_against_target(
    scanner,
    base_url: str,
    path: str = "/",
    method: str = "GET",
    credentials=None,
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
        parameters=None,
    )
    findings = await scanner.scan(target, endpoint, credentials)
    assert_findings_shape(findings)
    return findings
