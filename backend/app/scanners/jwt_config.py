"""JWT configuration scanner.

Inspects JSON Web Tokens returned by the target for basic configuration
weaknesses:
* ``alg: none`` acceptance (HIGH)
* missing ``exp`` claim (MEDIUM)
* signed with a weak, well-known secret (HIGH)

This is deliberately basic JWT *configuration* analysis only — token
cracking, algorithm-confusion exploitation, or other advanced JWT analysis
is out of scope (Deferred).
"""

import base64
import binascii
import json
import logging
import re

import httpx
import jwt

from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.jwt")

_OWASP_CATEGORY = "api8:2023"
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"
)
_WEAK_SECRETS = (
    "secret",
    "changeme",
    "password",
    "123456",
    "admin",
    "jwt",
    "apishield",
    "supersecret",
    "qwerty",
)


class JWTScanner(BaseScanner):
    """Inspect JWTs used/returned by the target for config weaknesses."""

    name = "jwt"
    description = "Inspects JWTs returned by the target for configuration weaknesses."

    async def scan(self, target, endpoint, credentials):
        url = f"{target.base_url}{endpoint.path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(endpoint.method, url)
        except httpx.RequestError as exc:
            logger.warning("JWTScanner could not reach %s: %s", url, exc)
            return []

        tokens = set(_JWT_RE.findall(response.text))
        findings: list[Finding] = []
        seen: set[str] = set()
        for token in tokens:
            for finding in _analyze_token(token, url):
                if finding.evidence not in seen:
                    findings.append(finding)
                    seen.add(finding.evidence)
        return findings


def _b64decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_parts(token: str) -> tuple[dict, dict]:
    header_b64, payload_b64, _ = token.split(".")
    header = json.loads(_b64decode(header_b64))
    payload = json.loads(_b64decode(payload_b64))
    return header, payload


def _signed_with_weak_secret(token: str, header: dict) -> bool:
    alg = header.get("alg")
    if alg not in {"HS256", "HS384", "HS512"}:
        return False
    for candidate in _WEAK_SECRETS:
        try:
            jwt.decode(
                token,
                candidate,
                algorithms=[alg],
                options={"verify_exp": False, "verify_signature": True},
            )
            return True
        except jwt.InvalidTokenError:
            continue
    return False


def _analyze_token(token: str, url: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        header, payload = _decode_parts(token)
    except (ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        return findings

    evidence = f"{token[:40]}..."
    alg = header.get("alg")
    if alg is None or str(alg).lower() == "none":
        findings.append(
            _finding(
                "JWT uses alg:none",
                url,
                evidence,
                Severity.HIGH,
            )
        )
    if "exp" not in payload:
        findings.append(
            _finding(
                "JWT missing exp claim",
                url,
                evidence,
                Severity.MEDIUM,
            )
        )
    if _signed_with_weak_secret(token, header):
        findings.append(
            _finding(
                "JWT signed with a weak known secret",
                url,
                evidence,
                Severity.HIGH,
            )
        )
    return findings


def _finding(title: str, url: str, evidence: str, severity: Severity) -> Finding:
    return Finding(
        title=title,
        description=(
            f"{title} on {url}. This is a security misconfiguration "
            "(OWASP API8)."
        ),
        severity=severity,
        evidence=f"{title}: {evidence}",
        owasp_category=_OWASP_CATEGORY,
        confidence=Confidence.HIGH,
    )
