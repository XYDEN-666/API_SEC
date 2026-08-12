"""Credential request/response schemas."""

from pydantic import BaseModel, Field


class CredentialCreate(BaseModel):
    identity_name: str = Field(min_length=1, max_length=255)
    auth_type: str = Field(min_length=1, max_length=50)
    value: str = Field(min_length=1, max_length=4096)


class CredentialResponse(BaseModel):
    id: int
    target_id: int
    identity_name: str
    auth_type: str
    masked_value: str
