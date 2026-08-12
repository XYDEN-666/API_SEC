"""Endpoint response schema."""

from pydantic import BaseModel, ConfigDict


class EndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    path: str
    method: str
    parameters: list | None
