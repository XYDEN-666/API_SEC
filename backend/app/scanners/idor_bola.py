"""IDOR/BOLA scanner: multi-identity request replay + response comparison.

For endpoints with an object identifier in the path (e.g. ``/users/{user_id}``),
the scanner replays the same request once per configured identity/credential
and compares the outcomes. Differing responses for the same object across
identities indicate a possible access-control anomaly (IDOR / Broken Object
Level Authorization, OWASP API1).

The scanner flags an access-control anomaly when:
* identities receive different response statuses for the same object, or
* two identities receive the same 2xx status with overlapping values in
  sensitive fields (e.g. a lower-privileged identity can read the same
  private data as a higher-privileged one).

The orchestrator provides the full credential set via ``scanner.credentials``;
the single ``credentials`` argument of :meth:`scan` is used as a fallback when
the scanner is driven directly. The scanner never touches the database — the
orchestrator persists its ``evidence_summary`` into the evidence row.
"""

import base64
import logging
import re
from itertools import combinations

import httpx

from app.core.crypto import decrypt_value
from app.scanners.base import BaseScanner, Confidence, Finding, Severity

logger = logging.getLogger("apishield.scanners.idor")

_OWASP_CATEGORY = "api1:2023"

DEFAULT_SENSITIVE_FIELDS = {
    "email",
    "ssn",
    "social_security_number",
    "account_number",
    "card_number",
    "credit_card",
    "password",
    "secret",
    "private_key",
    "token",
    "phone",
    "dob",
}


class IDORScanner(BaseScanner):
    """Replay object-identifier requests across identities."""

    name = "idor_bola"
    description = "Replays object-identifier requests across identities (IDOR/BOLA)."

    def __init__(self) -> None:
        self.credentials: list = []
        self.evidence_summary: str | None = None
        self.sensitive_fields: set[str] = set(DEFAULT_SENSITIVE_FIELDS)

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

        outcomes: list[dict] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for identity in identities:
                try:
                    response = await client.get(
                        url, headers=_auth_headers(identity)
                    )
                    outcomes.append(
                        {
                            "name": identity.identity_name,
                            "status": response.status_code,
                            "body": _parse_json(response),
                        }
                    )
                except httpx.RequestError as exc:
                    logger.warning(
                        "IDORScanner replay failed for %s on %s: %s",
                        identity.identity_name,
                        url,
                        exc,
                    )
                    outcomes.append(
                        {
                            "name": identity.identity_name,
                            "status": "error",
                            "body": None,
                        }
                    )

        self.evidence_summary = "; ".join(
            f"{outcome['name']} -> {outcome['status']}"
            for outcome in outcomes
        )

        findings: list[Finding] = []
        statuses = {outcome["status"] for outcome in outcomes}
        if len(statuses) > 1:
            findings.append(
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
            )

        for first, second in combinations(outcomes, 2):
            if (
                isinstance(first["status"], int)
                and first["status"] == second["status"]
                and 200 <= first["status"] < 300
                and isinstance(first["body"], dict)
                and isinstance(second["body"], dict)
            ):
                overlap = _sensitive_overlap(
                    first["body"],
                    second["body"],
                    self.sensitive_fields,
                )
                if overlap:
                    findings.append(
                        Finding(
                            title="Access-control anomaly detected (IDOR/BOLA)",
                            description=(
                                f"Identities {first['name']} and {second['name']} "
                                f"both received status {first['status']} for the "
                                f"same object ({url}) with overlapping sensitive "
                                f"field(s): {', '.join(overlap)}. This can indicate "
                                "broken object-level authorization (OWASP API1)."
                            ),
                            severity=Severity.MEDIUM,
                            evidence=(
                                f"status {first['status']} match; overlapping "
                                f"sensitive field(s): {', '.join(overlap)}"
                            ),
                            owasp_category=_OWASP_CATEGORY,
                            confidence=Confidence.HIGH,
                        )
                    )
        return findings


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


def _parse_json(response: httpx.Response) -> object:
    if "json" not in response.headers.get("content-type", ""):
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _collect_sensitive(body: object, sensitive: set[str]) -> dict[str, set]:
    """Recursively collect values for sensitive keys; returns key -> values."""
    collected: dict[str, set] = {}
    if isinstance(body, dict):
        for key, value in body.items():
            if key in sensitive and isinstance(
                value, (str, int, float, bool)
            ):
                collected.setdefault(key, set()).add(value)
            collected.update(_collect_sensitive(value, sensitive))
    elif isinstance(body, list):
        for item in body:
            collected.update(_collect_sensitive(item, sensitive))
    return collected


def _sensitive_overlap(
    body_a: dict,
    body_b: dict,
    sensitive: set[str],
) -> list[str]:
    """Return sensitive field names whose values overlap between two bodies."""
    values_a = _collect_sensitive(body_a, sensitive)
    values_b = _collect_sensitive(body_b, sensitive)
    return sorted(
        key
        for key in values_a
        if key in values_b and bool(values_a[key] & values_b[key])
    )
