"""Contract-only schemas for the future direct-to-S3 upload flow."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UploadFileRequest(BaseModel):
    relative_path: str
    size_bytes: int = Field(ge=0)
    content_type: str | None = None


class CreateUploadSessionRequest(BaseModel):
    files: list[UploadFileRequest] = Field(min_length=1)


class CreateProjectFromUploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class PlannedFeatureResponse(BaseModel):
    status: str = "NOT_IMPLEMENTED"
