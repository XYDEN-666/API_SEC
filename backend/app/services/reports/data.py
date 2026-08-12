"""Shared report data assembly for the HTML, PDF and JSON report formats.

One assembly path builds a plain :class:`ReportData` structure; the HTML
template renders from it, WeasyPrint converts that HTML to PDF, and the JSON
endpoint validates the same structure against the Pydantic report schema.
This guarantees the three formats describe the same scan content.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Evidence, Finding, Project, Scan, Target
from app.services.risk_scoring import risk_label, risk_score

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


@dataclass(frozen=True)
class ReportEvidenceData:
    """Evidence excerpt attached to a single finding."""

    evidence_id: int
    scanner_name: str
    request_data: str | None
    response_data: str | None
    timestamp: datetime | None


@dataclass(frozen=True)
class ReportFindingData:
    """One finding plus its risk score and evidence excerpt."""

    id: int
    scan_id: int
    title: str
    description: str
    severity: str
    endpoint: str
    evidence_id: int | None
    owasp_category: str
    confidence: str
    created_at: datetime
    risk_score: float
    risk_label: str
    evidence: ReportEvidenceData | None


@dataclass(frozen=True)
class ReportSummaryData:
    """Findings count by severity."""

    info: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0

    @property
    def total(self) -> int:
        return self.info + self.low + self.medium + self.high + self.critical


@dataclass(frozen=True)
class ReportMetadataData:
    """Scan/target/project metadata plus generation time."""

    scan_id: int
    target_id: int
    target_name: str
    base_url: str
    project_id: int
    project_name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    generated_at: datetime


@dataclass(frozen=True)
class ReportData:
    """Everything the report formats need."""

    metadata: ReportMetadataData
    summary: ReportSummaryData
    findings: list[ReportFindingData] = field(default_factory=list)


async def build_report_data(session: AsyncSession, scan_id: int) -> ReportData:
    """Load a scan's findings and evidence and assemble :class:`ReportData`.

    Findings are ordered by (OWASP category, severity, id) so the HTML
    template can group consecutive rows by category while keeping the most
    severe finding first within each category.
    """
    scan = await session.scalar(select(Scan).where(Scan.id == scan_id))
    if scan is None:
        raise LookupError(f"Scan {scan_id} not found")
    target = await session.scalar(
        select(Target).where(Target.id == scan.target_id)
    )
    project = (
        await session.scalar(
            select(Project).where(Project.id == target.project_id)
        )
        if target is not None
        else None
    )

    rows = (
        await session.scalars(
            select(Finding).where(Finding.scan_id == scan_id)
        )
    ).all()

    evidence_ids = {
        row.evidence_id for row in rows if row.evidence_id is not None
    }
    evidence_rows = (
        await session.scalars(
            select(Evidence).where(Evidence.id.in_(evidence_ids))
        )
        if evidence_ids
        else []
    )
    evidence_by_id = {row.id: row for row in evidence_rows}

    findings: list[ReportFindingData] = []
    for row in rows:
        score = risk_score(row.severity, row.confidence)
        evidence_row = (
            evidence_by_id.get(row.evidence_id)
            if row.evidence_id is not None
            else None
        )
        findings.append(
            ReportFindingData(
                id=row.id,
                scan_id=row.scan_id,
                title=row.title,
                description=row.description,
                severity=row.severity,
                endpoint=row.endpoint,
                evidence_id=row.evidence_id,
                owasp_category=row.owasp_category,
                confidence=row.confidence,
                created_at=row.created_at,
                risk_score=score,
                risk_label=risk_label(score),
                evidence=(
                    ReportEvidenceData(
                        evidence_id=evidence_row.id,
                        scanner_name=evidence_row.scanner_name,
                        request_data=evidence_row.request_data,
                        response_data=evidence_row.response_data,
                        timestamp=evidence_row.timestamp,
                    )
                    if evidence_row is not None
                    else None
                ),
            )
        )

    findings.sort(
        key=lambda f: (
            f.owasp_category,
            SEVERITY_ORDER.get(f.severity, 99),
            f.id,
        )
    )

    summary = ReportSummaryData(
        info=sum(f.severity == "info" for f in findings),
        low=sum(f.severity == "low" for f in findings),
        medium=sum(f.severity == "medium" for f in findings),
        high=sum(f.severity == "high" for f in findings),
        critical=sum(f.severity == "critical" for f in findings),
    )

    metadata = ReportMetadataData(
        scan_id=scan.id,
        target_id=target.id if target is not None else scan.target_id,
        target_name=target.name if target is not None else "Unknown target",
        base_url=target.base_url if target is not None else "",
        project_id=project.id if project is not None else 0,
        project_name=project.name if project is not None else "Unknown project",
        status=scan.status,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
        generated_at=datetime.now(timezone.utc),
    )

    return ReportData(metadata=metadata, summary=summary, findings=findings)
