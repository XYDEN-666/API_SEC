"""Target request/response schemas."""

from typing import Annotated
from urllib.parse import urlparse

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _validate_base_url(value: str) -> str:
    """Reject anything the scanners cannot resolve to an HTTP(S) request.

    The web UI already enforces this, but the API is the contract of record:
    a stored ``file://`` or relative URL would make every scanner silently
    no-op instead of failing loudly at the point the target is created.
    """
    trimmed = value.strip()
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "base_url must be an absolute http:// or https:// URL"
        )
    return trimmed


BaseUrl = Annotated[
    str,
    Field(min_length=1, max_length=2048),
    AfterValidator(_validate_base_url),
]


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: BaseUrl


class TargetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: BaseUrl


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    base_url: str
    name: str
