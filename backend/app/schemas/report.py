"""Structured JSON report schema (Task 11.3)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: int
    scanner_name: str
    request_data: str | None
    response_data: str | None
    timestamp: datetime | None


class ReportFinding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    evidence: ReportEvidence | None


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    info: int
    low: int
    medium: int
    high: int
    critical: int
    total: int


class ReportMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metadata: ReportMetadata
    summary: ReportSummary
    findings: list[ReportFinding]
