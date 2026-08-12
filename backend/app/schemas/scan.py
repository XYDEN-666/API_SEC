"""Scan response schema."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
