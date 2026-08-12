"""Finding deduplication for the persistence pipeline (Task 10.4).

A finding is a duplicate when the *same scanner* reports the *same issue*
for the *same endpoint* within a single scan. The dedup key is:

    (scan, endpoint, scanner type, normalized finding signature)

``scan`` pins the "scan target" component of the key: a scan belongs to
exactly one target, so the scan id is the target's scope within this
pipeline. The endpoint component includes the HTTP method so that e.g.
``GET /a`` and ``DELETE /a`` are never conflated.

The normalized signature identifies the issue itself: a whitespace- and
case-normalized title and description plus severity, OWASP category and
confidence. Evidence is deliberately excluded -- the same issue can be
observed across multiple requests with slightly different evidence
(captured headers, timestamps, response excerpts), and those observations
should collapse into one row rather than multiply.

Consequences of this key:
* The same issue on three different endpoints stays three rows.
* The same issue reported repeatedly on one endpoint collapses to one row.
"""

import re

from app.scanners.base import Finding as ScannerFinding

_WS_RE = re.compile(r"\s+")


def normalize_finding_signature(finding: ScannerFinding) -> str:
    """Return a case/whitespace-normalized signature for the issue.

    The signature is built from the finding's identity fields and excludes
    ``evidence``, so two observations of the same issue share a signature.
    """
    title = _WS_RE.sub(" ", (finding.title or "").strip().lower())
    description = _WS_RE.sub(" ", (finding.description or "").strip().lower())
    return "|".join(
        (
            title,
            description,
            finding.severity.value,
            finding.owasp_category or "",
            finding.confidence.value,
        )
    )


def finding_dedup_key(
    scan_id: int,
    endpoint: str,
    scanner_name: str,
    finding: ScannerFinding,
) -> tuple[int, str, str, str]:
    """Build the dedup key: (scan, endpoint, scanner type, signature)."""
    return (scan_id, endpoint, scanner_name, normalize_finding_signature(finding))


class FindingDeduplicator:
    """Track seen dedup keys so the pipeline persists each issue once.

    Usage (one instance per scan run):

        deduplicator = FindingDeduplicator(scan_id=scan.id)
        if deduplicator.is_duplicate(endpoint_url, scanner.name, finding):
            continue  # already persisted for this scan/endpoint/scanner
    """

    def __init__(self, scan_id: int) -> None:
        self._scan_id = scan_id
        self._seen: set[tuple[int, str, str, str]] = set()

    def is_duplicate(
        self,
        endpoint: str,
        scanner_name: str,
        finding: ScannerFinding,
    ) -> bool:
        """Return True if this issue was already seen, registering it if not."""
        key = finding_dedup_key(self._scan_id, endpoint, scanner_name, finding)
        if key in self._seen:
            return True
        self._seen.add(key)
        return False
