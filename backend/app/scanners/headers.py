"""Security Headers scanner (OWASP API8: Security Misconfiguration)."""

import logging
import re

import httpx

from app.scanners.base import BaseScanner, Confidence, Finding, Severity
from app.services.owasp_mapping import category_for_scanner

logger = logging.getLogger("apishield.scanners.headers")

_OWASP_CATEGORY = category_for_scanner("headers")
_HSTS_MAX_AGE = re.compile(r"max-age=(\d+)", re.IGNORECASE)
_ALLOWED_X_FRAME_OPTIONS = {"deny", "sameorigin"}


class HeaderScanner(BaseScanner):
    """Check security response headers on every endpoint.

    Verifies presence and basic correctness of:
    * Strict-Transport-Security (must include a positive ``max-age``)
    * X-Content-Type-Options (must be exactly ``nosniff``)
    * Content-Security-Policy (must be present and non-empty)
    * X-Frame-Options (must be ``DENY`` or ``SAMEORIGIN``)

    Missing or misconfigured headers produce MEDIUM/HIGH-confidence findings
    mapped to OWASP API8 (Security Misconfiguration).
    """

    name = "headers"
    description = "Checks for missing or misconfigured security response headers."

    async def scan(self, target, endpoint, credentials):
        url = f"{target.base_url}{endpoint.path}"
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=10.0
            ) as client:
                response = await client.request(endpoint.method, url)
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
