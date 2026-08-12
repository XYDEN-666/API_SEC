"""IDOR/BOLA scanner: multi-identity request replay.

For endpoints with an object identifier in the path (e.g. ``/users/{user_id}``),
the scanner replays the same request once per configured identity/credential
and compares the outcomes. Differing responses for the same object across
identities indicate a possible access-control anomaly (IDOR / Broken Object
Level Authorization, OWASP API1).

The orchestrator provides the full credential set via ``scanner.credentials``;
the single ``credentials`` argument of :meth:`scan` is used as a fallback when
the scanner is driven directly. The scanner never touches the database — the
orchestrator persists its ``evidence_summary`` into the evidence row.
"""

import base64
import logging
import re

import httpx

from app.core.crypto import decrypt_value
from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.idor")

_OWASP_CATEGORY = "api1:2023"


class IDORScanner(BaseScanner):
    """Replay object-identifier requests across identities."""

    name = "idor_bola"
    description = "Replays object-identifier requests across identities (IDOR/BOLA)."

    def __init__(self) -> None:
        self.credentials: list = []
        self.evidence_summary: str | None = None

    async def scan(self, target, endpoint, credentials):
        self.evidence_summary = None
        if endpoint is None:
            return []

        path_params = re.findall(r"\{([^}]+)\}", endpoint.path or "")
        if not path_params:
            # No object identifier in this endpoint — nothing to replay.
            return []

        identities = list(getattr(self, "credentials", []) or [])
        if not identities and credentials is not None:
            identities = [credentials]
        if not identities:
            return []

        sample_path = endpoint.path
        for name in path_params:
            sample_path = sample_path.replace("{" + name + "}", "1")
        url = f"{target.base_url}{sample_path}"

        outcomes: list[tuple[str, object]] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for identity in identities:
                try:
                    response = await client.get(
                        url, headers=_auth_headers(identity)
                    )
                    outcomes.append((identity.identity_name, response.status_code))
                except httpx.RequestError as exc:
                    logger.warning(
                        "IDORScanner replay failed for %s on %s: %s",
                        identity.identity_name,
                        url,
                        exc,
                    )
                    outcomes.append((identity.identity_name, f"error: {exc}"))

        self.evidence_summary = "; ".join(
            f"{name} -> {status}" for name, status in outcomes
        )

        statuses = {status for _, status in outcomes}
        if len(statuses) <= 1:
            return []
        return [
            Finding(
                title="Access-control anomaly detected (IDOR/BOLA)",
                description=(
                    f"Requesting the same object ({url}) produced different "
                    "responses across identities, which can indicate a broken "
                    "object-level authorization (OWASP API1)."
                ),
                severity=Severity.MEDIUM,
                evidence=self.evidence_summary,
                owasp_category=_OWASP_CATEGORY,
                confidence=Confidence.MEDIUM,
            )
        ]


def _auth_headers(credential) -> dict[str, str]:
    """Build request headers for a credential (decryption is internal only)."""
    value = decrypt_value(credential.encrypted_value)
    auth_type = credential.auth_type.lower()
    if auth_type == "bearer":
        return {"Authorization": f"Bearer {value}"}
    if auth_type == "basic":
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}
    return {"X-API-Key": value}  # api_key and default
