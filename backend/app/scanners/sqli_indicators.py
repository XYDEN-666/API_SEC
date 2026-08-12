"""SQL Injection indicator scanner (error-based detection only).

Sends common injection payloads through parameterized endpoints and looks for
database error signatures in the responses (SQLSTATE codes, "syntax error
near/at or near", SQL driver stack traces). This is error-based indicator
detection only — time-based SQLi is Deferred scope and is NOT built here.
"""

import logging
import re
from urllib.parse import quote

import httpx

from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.sqli")

_OWASP_CATEGORY = "api8:2023"

_PAYLOADS = (
    "'",
    '"\'',
    "' OR '1'='1",
    "' OR 1=1--",
    "1' AND '1'='1",
    "' UNION SELECT NULL--",
    "\"; DROP TABLE users;--",
)

_DB_ERROR_SIGNATURES = (
    "sqlstate[",
    "sqlstate ",
    "syntax error near",
    "syntax error at or near",
    "psycopg",
    "sqlalchemy.exc",
    "operationalerror",
    "programmingerror",
    "sqlite3",
    "traceback (most recent call last)",
    "postgresql",
    "odbc",
    "oledb",
)


class SQLiScanner(BaseScanner):
    """Probe parameterized endpoints with injection payloads and detect
    error-based SQL injection indicators."""

    name = "sqli_indicators"
    description = "Detects error-based SQL injection indicators."

    async def scan(self, target, endpoint, credentials):
        if endpoint is None:
            return []

        findings: list[Finding] = []
        seen: set[tuple[str, str]] = set()
        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in _injection_urls(target, endpoint):
                try:
                    response = await client.get(url)
                except httpx.RequestError as exc:
                    logger.debug("SQLi probe failed for %s: %s", url, exc)
                    continue

                body = response.text.lower()
                matched = next(
                    (sig for sig in _DB_ERROR_SIGNATURES if sig in body),
                    None,
                )
                if matched is None:
                    continue
                key = (url.split("?")[0], matched)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    _finding(
                        "SQL injection indicator detected",
                        url,
                        f"DB error signature {matched!r} in response",
                    )
                )
        return findings


def _injection_urls(target, endpoint) -> list[str]:
    """Build the candidate URLs with payloads in path and query parameters."""
    urls: list[str] = []
    path = endpoint.path or "/"

    for param_name in re.findall(r"\{([^}]+)\}", path):
        for payload in _PAYLOADS:
            injected = path.replace(
                "{" + param_name + "}", quote(payload, safe="")
            )
            urls.append(f"{target.base_url}{injected}")

    query_params = [
        parameter
        for parameter in (endpoint.parameters or [])
        if isinstance(parameter, dict)
        and parameter.get("in") == "query"
        and parameter.get("name")
    ]
    for parameter in query_params:
        for payload in _PAYLOADS:
            urls.append(
                f"{target.base_url}{path}"
                f"?{parameter['name']}={quote(payload, safe='')}"
            )
    return urls


def _finding(title: str, url: str, evidence: str) -> Finding:
    return Finding(
        title=title,
        description=(
            f"{title} on {url}. An injection payload produced a database "
            "error signature, indicating error-based SQL injection."
        ),
        severity=Severity.HIGH,
        evidence=f"{title}: {evidence} ({url})",
        owasp_category=_OWASP_CATEGORY,
        confidence=Confidence.HIGH,
    )
