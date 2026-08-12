"""Authorization record request/response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class AuthorizationRecordCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    scope_notes: str | None = Field(default=None, max_length=5000)


class AuthorizationRecordUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    scope_notes: str | None = Field(default=None, max_length=5000)


class AuthorizationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    description: str
    scope_notes: str | None
