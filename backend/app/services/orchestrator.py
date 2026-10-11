"""Scan orchestration: drives registered scanners across a target's endpoints
and persists scan/evidence records."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Credential, Endpoint, Evidence, Finding, Scan, Target
from app.scanners.base import BaseScanner, Finding as ScannerFinding
from app.scanners.cors import CORSScanner
from app.scanners.headers import HeaderScanner
from app.scanners.http_methods import HTTPMethodScanner
from app.scanners.idor_bola import IDORScanner
from app.scanners.jwt_config import JWTScanner
from app.scanners.sqli_indicators import SQLiScanner
from app.services.deduplication import FindingDeduplicator
from app.services.owasp_mapping import category_for_scanner

logger = logging.getLogger("apishield.orchestrator")

_DEFAULT_SCANNER_CLASSES: tuple[type[BaseScanner], ...] = (
    HeaderScanner,
    CORSScanner,
    HTTPMethodScanner,
    IDORScanner,
    JWTScanner,
    SQLiScanner,
)


def _endpoint_url(target: Target, endpoint: Endpoint | None) -> str:
    """Canonical identifier for the thing that was scanned.

    Method-qualified for per-endpoint scans (so GET /a and DELETE /a stay
    distinguishable), and the bare base URL for target-level scans, which are
    a statement about the API as a whole rather than about one operation.
    """
    if endpoint is None:
        return target.base_url
    return f"{endpoint.method} {target.base_url}{endpoint.path}"


@dataclass
class ScanResult:
    """Outcome of an orchestrated scan run."""

    scan_id: int
    findings: list[ScannerFinding] = field(default_factory=list)
    errors: int = 0


class ScanOrchestrator:
    """Run every enabled scanner against a target's endpoints.

    The orchestrator owns the plumbing: loading the target's endpoints and
    credentials from the database, invoking each scanner's ``scan()`` per
    endpoint, and collecting the findings. Scanners never touch this class or
    any persistence layer directly.
    """

    def __init__(
        self,
        scanners: Iterable[BaseScanner] | None = None,
        scanner_timeout: float = 30.0,
    ) -> None:
        if scanners is None:
            self.scanners = [scanner_cls() for scanner_cls in _DEFAULT_SCANNER_CLASSES]
        else:
            self.scanners = list(scanners)
        self.scanner_timeout = scanner_timeout

    def register(self, scanner: BaseScanner) -> None:
        """Enable a scanner for subsequent runs."""
        self.scanners.append(scanner)

    async def run_scan(
        self,
        target: Target,
        session: AsyncSession,
        scan_id: int | None = None,
    ) -> ScanResult:
        """Scan ``target`` with every registered scanner.

        Args:
            target: The target being scanned.
            session: Async DB session used to load the target's endpoints
                and credentials.
            scan_id: Reuse an existing Scan row (typically one the API already
                created with status ``queued``) instead of creating a new one.
                The scan API needs a real id to hand back immediately, so it
                creates the row and the worker runs against it.

        Returns:
            A :class:`ScanResult` with the persisted scan id and all findings.
            With no scanners registered this is an empty result, which still
            proves the orchestration plumbing works.
        """
        endpoints = list(
            await session.scalars(
                select(Endpoint).where(Endpoint.target_id == target.id)
            )
        )
        credentials = list(
            await session.scalars(
                select(Credential).where(Credential.target_id == target.id)
            )
        )
        credential = credentials[0] if credentials else None

        if scan_id is None:
            scan = Scan(target_id=target.id, status="running")
            session.add(scan)
            await session.flush()
        else:
            scan = await session.get(Scan, scan_id)
            if scan is None:
                raise LookupError(f"Scan {scan_id} not found")
            scan.status = "running"
        scan_id = scan.id
        deduplicator = FindingDeduplicator(scan_id=scan_id)

        findings: list[ScannerFinding] = []
        scan_errors = 0
        for scanner in self.scanners:
            # Provide the full credential set for multi-identity scanners.
            scanner.credentials = credentials
            # A target-level scanner inspects the API as a whole, so it runs
            # once with no endpoint instead of once per operation.
            units: list[Endpoint | None] = (
                [None] if scanner.target_level else endpoints
            )
            for endpoint in units:
                endpoint_url = _endpoint_url(target, endpoint)
                try:
                    scanner_findings = await asyncio.wait_for(
                        scanner.scan(target, endpoint, credential),
                        timeout=self.scanner_timeout,
                    )
                except asyncio.TimeoutError:
                    # A scanner that exceeds its budget must not stall the
                    # scan; record the failure and move on.
                    scan_errors += 1
                    logger.warning(
                        "Scanner %s timed out on %s",
                        scanner.name,
                        endpoint_url,
                    )
                    session.add(
                        Evidence(
                            scan_id=scan.id,
                            scanner_name=scanner.name,
                            request_data=endpoint_url,
                            response_data=json.dumps({"error": "timeout"}),
                        )
                    )
                    continue
                except Exception as exc:
                    # One failing scanner must not abort the whole scan run.
                    scan_errors += 1
                    logger.exception(
                        "Scanner %s failed on %s",
                        scanner.name,
                        endpoint_url,
                    )
                    session.add(
                        Evidence(
                            scan_id=scan.id,
                            scanner_name=scanner.name,
                            request_data=endpoint_url,
                            response_data=json.dumps({"error": str(exc)}),
                        )
                    )
                    continue
                # Collapse true duplicates (same scanner, same endpoint, same
                # issue) while keeping per-endpoint findings distinct. The key
                # includes the HTTP method, so GET /a and DELETE /a never
                # collapse into one another.
                unique_findings = [
                    finding
                    for finding in scanner_findings
                    if not deduplicator.is_duplicate(
                        endpoint_url, scanner.name, finding
                    )
                ]
                response_data: dict[str, object] = {
                    "findings_count": len(unique_findings)
                }
                summary = getattr(scanner, "evidence_summary", None)
                if summary:
                    response_data["summary"] = summary
                evidence = Evidence(
                    scan_id=scan.id,
                    scanner_name=scanner.name,
                    request_data=endpoint_url,
                    response_data=json.dumps(response_data),
                )
                session.add(evidence)
                await session.flush()
                for finding in unique_findings:
                    findings.append(finding)
                    session.add(
                        Finding(
                            scan_id=scan.id,
                            title=finding.title,
                            description=finding.description,
                            severity=finding.severity.value,
                            # Persist the same method-qualified identifier the
                            # deduplicator keys on. Storing the bare URL here
                            # would make two distinct operations on one path
                            # (e.g. GET and PUT /projects/{id}) render as
                            # identical rows, which is a misleading duplicate.
                            endpoint=endpoint_url,
                            evidence_id=evidence.id,
                            # Fall back to the registered mapping so a
                            # third-party scanner can never persist a finding
                            # without a non-null OWASP category.
                            owasp_category=(
                                finding.owasp_category
                                or category_for_scanner(scanner.name)
                            ),
                            confidence=finding.confidence.value,
                            # Persist the scanner's own proof text; without it
                            # the report can only show the endpoint URL and a
                            # finding count.
                            evidence_text=finding.evidence,
                        )
                    )

        scan.status = "completed" if scan_errors == 0 else "completed_with_errors"
        scan.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return ScanResult(scan_id=scan_id, findings=findings, errors=scan_errors)
