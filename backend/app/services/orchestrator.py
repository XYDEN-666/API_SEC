"""Scan orchestration: drives registered scanners across a target's endpoints."""

import logging
from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Credential, Endpoint, Target
from app.scanners.base import BaseScanner, Finding

logger = logging.getLogger("apishield.orchestrator")


@dataclass
class ScanResult:
    """Outcome of an orchestrated scan run."""

    findings: list[Finding] = field(default_factory=list)


class ScanOrchestrator:
    """Run every enabled scanner against a target's endpoints.

    The orchestrator owns the plumbing: loading the target's endpoints and
    credentials from the database, invoking each scanner's ``scan()`` per
    endpoint, and collecting the findings. Scanners never touch this class or
    any persistence layer directly.
    """

    def __init__(self, scanners: Iterable[BaseScanner] | None = None) -> None:
        self.scanners: list[BaseScanner] = list(scanners or [])

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
            A :class:`ScanResult` with all findings. With no scanners
            registered this is an empty result, which still proves the
            orchestration plumbing works.
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

        findings: list[Finding] = []
        for scanner in self.scanners:
            for endpoint in endpoints:
                try:
                    findings.extend(
                        await scanner.scan(target, endpoint, credential)
                    )
                except Exception:
                    # One failing scanner must not abort the whole scan run.
                    logger.exception(
                        "Scanner %s failed on %s %s",
                        scanner.name,
                        endpoint.method,
                        endpoint.path,
                    )
        return ScanResult(findings=findings)
