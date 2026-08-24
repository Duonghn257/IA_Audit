"""Local-first upload sessions and object-download placeholder routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.audit_errors import audit_api_errors, feature_unavailable
from app.api.dependencies import (
    CurrentPrincipalDependency,
    get_audit_intake_service,
)
from app.api.schemas.upload_sessions import (
    CreateProjectFromUploadRequest,
    CreateProjectFromUploadResponse,
    CreateUploadSessionRequest,
    UploadFileResponse,
    UploadSessionResponse,
)
from app.application.audit_intake_service import (
    AuditIntakeService,
    UploadFileDescriptor,
)

router = APIRouter(tags=["upload-sessions"])
AuditIntakeDependency = Annotated[
    AuditIntakeService,
    Depends(get_audit_intake_service),
]


@router.post(
    "/upload-sessions",
    response_model=UploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_upload_session(
    request: CreateUploadSessionRequest,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> UploadSessionResponse:
    with audit_api_errors():
        view = service.create_session(
            [
                UploadFileDescriptor(
                    relative_path=file.relative_path,
                    size_bytes=file.size_bytes,
                    content_type=file.content_type,
                    modified_at=file.modified_at,
                )
                for file in request.files
            ],
            actor_id=principal.user.user_id,
            actor_label=principal.user.display_name,
            actor_type=principal.user.provider,
        )
        return UploadSessionResponse.from_view(view)


@router.put(
    "/upload-sessions/{session_id}/files/{file_id}",
    response_model=UploadFileResponse,
)
async def upload_session_file(
    session_id: str,
    file_id: str,
    request: Request,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> UploadFileResponse:
    with audit_api_errors():
        view = await service.upload_file(
            session_id,
            file_id,
            request.stream(),
            actor_id=principal.user.user_id,
        )
        return UploadFileResponse.from_view(view)


@router.get(
    "/upload-sessions/{session_id}",
    response_model=UploadSessionResponse,
)
def get_upload_session(
    session_id: str,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> UploadSessionResponse:
    with audit_api_errors():
        return UploadSessionResponse.from_view(
            service.get_session(
                session_id,
                actor_id=principal.user.user_id,
            )
        )


@router.post(
    "/upload-sessions/{session_id}/validate",
    response_model=UploadSessionResponse,
)
def validate_upload_session(
    session_id: str,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> UploadSessionResponse:
    with audit_api_errors():
        return UploadSessionResponse.from_view(
            service.validate_session(
                session_id,
                actor_id=principal.user.user_id,
            )
        )


@router.post(
    "/upload-sessions/{session_id}/projects",
    response_model=CreateProjectFromUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_from_upload(
    session_id: str,
    request: CreateProjectFromUploadRequest,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> CreateProjectFromUploadResponse:
    with audit_api_errors():
        return CreateProjectFromUploadResponse.from_result(
            service.promote_session(
                session_id,
                request.name,
                actor_id=principal.user.user_id,
            )
        )


@router.delete(
    "/upload-sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_upload_session(
    session_id: str,
    service: AuditIntakeDependency,
    principal: CurrentPrincipalDependency,
) -> None:
    with audit_api_errors():
        service.discard_session(
            session_id,
            actor_id=principal.user.user_id,
        )


@router.get("/outputs/{output_id}/download", response_model=None)
def download_output(output_id: str):
    del output_id
    raise feature_unavailable(
        "S3_STORAGE_NOT_CONFIGURED",
        "Versioned output download is not implemented yet.",
    )
