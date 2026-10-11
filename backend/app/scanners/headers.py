"""Security Headers scanner (OWASP API8: Security Misconfiguration)."""

import logging
import re

import httpx

from app.scanners.auth import auth_headers
from app.scanners.base import BaseScanner, Confidence, Finding, Severity
from app.services.owasp_mapping import category_for_scanner

logger = logging.getLogger("apishield.scanners.headers")

_OWASP_CATEGORY = category_for_scanner("headers")
_HSTS_MAX_AGE = re.compile(r"max-age=(\d+)", re.IGNORECASE)
_ALLOWED_X_FRAME_OPTIONS = {"deny", "sameorigin"}


class HeaderScanner(BaseScanner):
    """Check security response headers for the API as a whole.

    Verifies presence and basic correctness of:
    * Strict-Transport-Security (must include a positive ``max-age``)
    * X-Content-Type-Options (must be exactly ``nosniff``)
    * Content-Security-Policy (must be present and non-empty)
    * X-Frame-Options (must be ``DENY`` or ``SAMEORIGIN``)

    Headers are emitted by the server, not by an individual operation, so this
    is a *target-level* scanner: it probes the target's base URL once instead
    of once per endpoint. Without that, a single host-wide gap (say, no
    Content-Security-Policy anywhere) would be reported once per operation --
    32 near-identical findings for a 32-operation API.

    Missing or misconfigured headers produce MEDIUM/HIGH-confidence findings
    mapped to OWASP API8 (Security Misconfiguration).
    """

    name = "headers"
    description = "Checks for missing or misconfigured security response headers."
    target_level = True

    async def scan(self, target, endpoint, credentials):
        url = _probe_url(target, endpoint)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=10.0
            ) as client:
                response = await client.request(
                    endpoint.method if endpoint is not None else "GET",
                    url,
                    headers=auth_headers(credentials),
                )
        except httpx.RequestError as exc:
            logger.warning("HeaderScanner could not reach %s: %s", url, exc)
            return []

        headers = response.headers
        findings: list[Finding] = []

        hsts = headers.get("strict-transport-security")
        if hsts is None:
            findings.append(
                self._finding("Missing Strict-Transport-Security", url, "not present")
            )
        else:
            match = _HSTS_MAX_AGE.search(hsts)
            if match is None or int(match.group(1)) <= 0:
                findings.append(
                    self._finding(
                        "Misconfigured Strict-Transport-Security", url, hsts
                    )
                )

        xcto = headers.get("x-content-type-options")
        if xcto is None:
            findings.append(
                self._finding("Missing X-Content-Type-Options", url, "not present")
            )
        elif xcto.strip().lower() != "nosniff":
            findings.append(
                self._finding("Misconfigured X-Content-Type-Options", url, xcto)
            )

        csp = headers.get("content-security-policy")
        if csp is None or not csp.strip():
            findings.append(
                self._finding(
                    "Missing Content-Security-Policy",
                    url,
                    "not present" if csp is None else "empty value",
                )
            )

        xfo = headers.get("x-frame-options")
        if xfo is None:
            findings.append(
                self._finding("Missing X-Frame-Options", url, "not present")
            )
        elif xfo.strip().lower() not in _ALLOWED_X_FRAME_OPTIONS:
            findings.append(
                self._finding("Misconfigured X-Frame-Options", url, xfo)
            )

        return findings

    @staticmethod
    def _finding(title: str, url: str, evidence: str) -> Finding:
        return Finding(
            title=title,
            description=(
                f"{title} on {url}. This is a security misconfiguration "
                "(OWASP API8)."
            ),
            severity=Severity.MEDIUM,
            evidence=f"{title}: {evidence}",
            owasp_category=_OWASP_CATEGORY,
            confidence=Confidence.HIGH,
        )


def _probe_url(target, endpoint) -> str:
    """URL to inspect: the endpoint's own path, or the target's base URL.

    The orchestrator calls a target-level scanner with ``endpoint=None``;
    direct calls (and the scanner test harness) still pass an endpoint, and
    both behaviours are supported.
    """
    if endpoint is None:
        return target.base_url
    return f"{target.base_url}{endpoint.path}"
