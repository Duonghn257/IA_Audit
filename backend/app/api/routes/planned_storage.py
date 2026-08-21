"""Published API contract for endpoints blocked by the unavailable S3 bucket."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.audit_errors import feature_unavailable
from app.api.schemas.upload_sessions import (
    CreateProjectFromUploadRequest,
    CreateUploadSessionRequest,
    PlannedFeatureResponse,
)

router = APIRouter(tags=["upload-sessions"])


def _s3_unavailable():
    raise feature_unavailable(
        "S3_STORAGE_NOT_CONFIGURED",
        "This endpoint is in the API contract but cannot run until "
        "an S3 bucket and credentials are configured.",
    )


@router.post(
    "/upload-sessions",
    response_model=PlannedFeatureResponse,
    status_code=status.HTTP_201_CREATED,
    responses={501: {"description": "S3 storage is not configured"}},
)
def create_upload_session(request: CreateUploadSessionRequest) -> PlannedFeatureResponse:
    del request
    return _s3_unavailable()


@router.get("/upload-sessions/{session_id}", response_model=PlannedFeatureResponse)
def get_upload_session(session_id: str) -> PlannedFeatureResponse:
    del session_id
    return _s3_unavailable()


@router.post(
    "/upload-sessions/{session_id}/validate",
    response_model=PlannedFeatureResponse,
)
def validate_upload_session(session_id: str) -> PlannedFeatureResponse:
    del session_id
    return _s3_unavailable()


@router.post(
    "/upload-sessions/{session_id}/projects",
    response_model=PlannedFeatureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_from_upload(
    session_id: str,
    request: CreateProjectFromUploadRequest,
) -> PlannedFeatureResponse:
    del session_id, request
    return _s3_unavailable()


@router.delete("/upload-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload_session(session_id: str) -> None:
    del session_id
    _s3_unavailable()


@router.get("/outputs/{output_id}/download", response_model=None)
def download_output(output_id: str):
    del output_id
    return _s3_unavailable()
