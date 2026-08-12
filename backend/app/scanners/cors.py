"""CORS scanner: detects overly permissive cross-origin configurations."""

import logging

import httpx

from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.cors")

_OWASP_CATEGORY = "api8:2023"
_ATTACKER_ORIGIN = "https://evil.example"


class CORSScanner(BaseScanner):
    """Check Access-Control-Allow-* headers for overly permissive configs.

    Sends a simple request and an OPTIONS preflight with an attacker-controlled
    Origin and flags:
    * ``Access-Control-Allow-Origin: *`` combined with credentials (HIGH)
    * ``Access-Control-Allow-Origin: *`` alone (MEDIUM)
    * ``Access-Control-Allow-Origin: null`` (MEDIUM)
    * A reflected/attacker origin combined with credentials (HIGH)

    Properly restricted configs (specific allowed origins, no credentials with
    wildcards) produce no findings.
    """

    name = "cors"
    description = "Checks CORS headers for overly permissive configurations."

    async def scan(self, target, endpoint, credentials):
        url = f"{target.base_url}{endpoint.path}"
        origin_headers = {"Origin": _ATTACKER_ORIGIN}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                simple = await client.request(
                    endpoint.method, url, headers=origin_headers
                )
                preflight = await client.options(
                    url,
                    headers={
                        **origin_headers,
                        "Access-Control-Request-Method": endpoint.method,
                    },
                )
        except httpx.RequestError as exc:
            logger.warning("CORSScanner could not reach %s: %s", url, exc)
            return []

        findings = _evaluate_cors(simple, url)
        seen = {finding.evidence for finding in findings}
        for finding in _evaluate_cors(preflight, url):
            if finding.evidence not in seen:
                findings.append(finding)
                seen.add(finding.evidence)
        return findings


def _evaluate_cors(response: httpx.Response, url: str) -> list[Finding]:
    """Return findings for one HTTP response's CORS headers."""
    acao = response.headers.get("access-control-allow-origin")
    if acao is None:
        return []
    acao = acao.strip()
    acac = (
        response.headers.get("access-control-allow-credentials", "")
        .strip()
        .lower()
    )
    credentials_allowed = acac == "true"

    findings: list[Finding] = []
    if acao == "*":
        if credentials_allowed:
            findings.append(
                _finding(
                    "Wildcard CORS origin combined with credentials",
                    url,
                    f"ACAO: * | ACAC: {acac}",
                    Severity.HIGH,
                )
            )
        else:
            findings.append(
                _finding(
                    "Wildcard CORS origin",
                    url,
                    "ACAO: *",
                    Severity.MEDIUM,
                )
            )
    elif acao.lower() == "null":
        findings.append(
            _finding(
                "Null CORS origin",
                url,
                f"ACAO: null | ACAC: {acac}",
                Severity.MEDIUM,
            )
        )
    elif acao == _ATTACKER_ORIGIN and credentials_allowed:
        findings.append(
            _finding(
                "Reflected CORS origin combined with credentials",
                url,
                f"ACAO: {acao} | ACAC: true",
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
