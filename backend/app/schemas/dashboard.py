"""Dashboard aggregation response schemas (Task 13.1)."""

from datetime import datetime

from pydantic import BaseModel


class TopFinding(BaseModel):
    """The highest-severity finding of a scan."""

    title: str
    severity: str


class RecentScan(BaseModel):
    """One recent scan with its target and top finding."""

    id: int
    target_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    top_finding: TopFinding | None


class DashboardSummary(BaseModel):
    """Owner-scoped aggregate stats across the user's projects."""

    total_projects: int
    total_targets: int
    total_scans: int
    total_findings: int
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    recent_scans: list[RecentScan]
