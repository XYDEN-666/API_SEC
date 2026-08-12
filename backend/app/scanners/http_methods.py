"""HTTP Methods scanner: probes for unexpectedly enabled methods."""

import logging

import httpx

from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.http_methods")

_OWASP_CATEGORY = "api8:2023"


class HTTPMethodScanner(BaseScanner):
    """Probe OPTIONS/TRACE/PUT/DELETE and flag unexpectedly enabled methods.

    A method is considered "enabled" when the server responds with anything
    other than 404/405/501 (i.e. it actually handled the request). TRACE is
    the most dangerous (XST) and is HIGH; PUT/DELETE are MEDIUM. OPTIONS is
    reported only when it advertises dangerous methods via the Allow header.
    """

    name = "http_methods"
    description = "Probes for unexpectedly enabled HTTP methods."

    _PROBED_METHODS = ("OPTIONS", "TRACE", "PUT", "DELETE")
    _NOT_ENABLED_STATUSES = {404, 405, 501}
    _DANGEROUS_ADVERTISED = {"TRACE", "PUT", "DELETE", "PATCH", "DEBUG"}

    async def scan(self, target, endpoint, credentials):
        url = f"{target.base_url}{endpoint.path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                responses = {
                    method: await client.request(method, url)
                    for method in self._PROBED_METHODS
                }
        except httpx.RequestError as exc:
            logger.warning(
                "HTTPMethodScanner could not reach %s: %s", url, exc
            )
            return []

        findings: list[Finding] = []
        for method in ("TRACE", "PUT", "DELETE"):
            response = responses[method]
            if response.status_code in self._NOT_ENABLED_STATUSES:
                continue
            severity = Severity.HIGH if method == "TRACE" else Severity.MEDIUM
            findings.append(
                self._finding(
                    f"{method} method enabled",
                    url,
                    f"{method} {url} -> {response.status_code}",
                    severity,
                )
            )

        allow = responses["OPTIONS"].headers.get("allow", "")
        advertised = [
            method
            for method in self._DANGEROUS_ADVERTISED
            if method in allow.upper()
        ]
        if advertised:
            findings.append(
                self._finding(
                    "OPTIONS advertises dangerous methods",
                    url,
                    f"Allow: {allow}",
                    Severity.MEDIUM,
                )
            )
        return findings

    @staticmethod
    def _finding(
        title: str, url: str, evidence: str, severity: Severity
    ) -> Finding:
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
