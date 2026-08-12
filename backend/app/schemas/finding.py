"""Finding response schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FindingResponse(BaseModel):
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
