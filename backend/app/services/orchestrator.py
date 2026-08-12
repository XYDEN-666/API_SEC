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

from app.models import Credential, Endpoint, Evidence, Scan, Target
from app.scanners.base import BaseScanner, Finding
from app.scanners.cors import CORSScanner
from app.scanners.headers import HeaderScanner
from app.scanners.http_methods import HTTPMethodScanner
from app.scanners.jwt_config import JWTScanner
from app.scanners.sqli_indicators import SQLiScanner

logger = logging.getLogger("apishield.orchestrator")

_DEFAULT_SCANNER_CLASSES: tuple[type[BaseScanner], ...] = (
    HeaderScanner,
    CORSScanner,
    HTTPMethodScanner,
    JWTScanner,
    SQLiScanner,
)


@dataclass
class ScanResult:
    """Outcome of an orchestrated scan run."""

    scan_id: int
    findings: list[Finding] = field(default_factory=list)
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
    ) -> ScanResult:
        """Scan ``target`` with every registered scanner.

        Args:
            target: The target being scanned.
            session: Async DB session used to load the target's endpoints
                and credentials.

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

        scan = Scan(target_id=target.id, status="running")
        session.add(scan)
        await session.flush()
        scan_id = scan.id

        findings: list[Finding] = []
        scan_errors = 0
        for scanner in self.scanners:
            for endpoint in endpoints:
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
                        "Scanner %s timed out on %s %s",
                        scanner.name,
                        endpoint.method,
                        endpoint.path,
                    )
                    session.add(
                        Evidence(
                            scan_id=scan.id,
                            scanner_name=scanner.name,
                            request_data=(
                                f"{endpoint.method} "
                                f"{target.base_url}{endpoint.path}"
                            ),
                            response_data=json.dumps({"error": "timeout"}),
                        )
                    )
                    continue
                except Exception as exc:
                    # One failing scanner must not abort the whole scan run.
                    scan_errors += 1
                    logger.exception(
                        "Scanner %s failed on %s %s",
                        scanner.name,
                        endpoint.method,
                        endpoint.path,
                    )
                    session.add(
                        Evidence(
                            scan_id=scan.id,
                            scanner_name=scanner.name,
                            request_data=(
                                f"{endpoint.method} "
                                f"{target.base_url}{endpoint.path}"
                            ),
                            response_data=json.dumps({"error": str(exc)}),
                        )
                    )
                    continue
                findings.extend(scanner_findings)
                session.add(
                    Evidence(
                        scan_id=scan.id,
                        scanner_name=scanner.name,
                        request_data=(
                            f"{endpoint.method} "
                            f"{target.base_url}{endpoint.path}"
                        ),
                        response_data=json.dumps(
                            {"findings_count": len(scanner_findings)}
                        ),
                    )
                )

        scan.status = "completed" if scan_errors == 0 else "completed_with_errors"
        scan.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return ScanResult(scan_id=scan_id, findings=findings, errors=scan_errors)
