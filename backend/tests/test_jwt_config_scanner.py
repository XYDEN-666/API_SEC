"""JWT configuration scanner tests using the smoke-test harness."""

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt

from app.scanners.jwt_config import JWTScanner
from tests.scanner_harness import run_scanner_against_target


def _scan(scanner, base_url):
    return asyncio.run(run_scanner_against_target(scanner, base_url))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_alg_none_token() -> str:
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": "1"}).encode())
    return f"{header}.{payload}."


def test_token_missing_exp_produces_finding(http_target_factory) -> None:
    token = jwt.encode(
        {"sub": "1"},
        "reasonable-secret-0123456789",
        algorithm="HS256",
    )
    base_url = http_target_factory(body={"token": token})

    findings = _scan(JWTScanner(), base_url)
    titles = {finding.title for finding in findings}

    assert "JWT missing exp claim" in titles
    finding = next(f for f in findings if f.title == "JWT missing exp claim")
    assert finding.severity.value == "medium"
    assert finding.owasp_category == "api8:2023"


def test_well_formed_token_produces_no_findings(http_target_factory) -> None:
    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "reasonable-secret-0123456789",
        algorithm="HS256",
    )
    base_url = http_target_factory(body={"token": token})

    assert _scan(JWTScanner(), base_url) == []


def test_alg_none_produces_high_finding(http_target_factory) -> None:
    base_url = http_target_factory(body={"token": _make_alg_none_token()})

    findings = _scan(JWTScanner(), base_url)
    assert any("alg:none" in finding.title for finding in findings)
    alg_none = next(f for f in findings if "alg:none" in f.title)
    assert alg_none.severity.value == "high"


def test_weak_secret_produces_high_finding(http_target_factory) -> None:
    token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "secret",
        algorithm="HS256",
    )
    base_url = http_target_factory(body={"token": token})

    findings = _scan(JWTScanner(), base_url)
    assert any("weak known secret" in finding.title for finding in findings)
    weak = next(f for f in findings if "weak known secret" in f.title)
    assert weak.severity.value == "high"
