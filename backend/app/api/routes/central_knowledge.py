"""Manage app-wide current Guidelines and template.docx."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from app.api.audit_errors import audit_api_errors
from app.api.dependencies import (
    CurrentPrincipalDependency,
    get_central_knowledge_service,
)
from app.api.schemas.central_knowledge import (
    CentralAssetResponse,
    CentralKnowledgeResponse,
)
from app.application.central_knowledge_service import CentralKnowledgeService

router = APIRouter(prefix="/central-knowledge", tags=["central-knowledge"])
CentralKnowledgeDependency = Annotated[
    CentralKnowledgeService,
    Depends(get_central_knowledge_service),
]


@router.get("", response_model=CentralKnowledgeResponse)
def get_central_knowledge(
    service: CentralKnowledgeDependency,
) -> CentralKnowledgeResponse:
    with audit_api_errors():
        return CentralKnowledgeResponse.from_domain(service.get_current())


@router.post(
    "/guidelines",
    response_model=CentralAssetResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_guideline(
    principal: CurrentPrincipalDependency,
    service: CentralKnowledgeDependency,
    file: Annotated[UploadFile, File(...)],
) -> CentralAssetResponse:
    with audit_api_errors():
        content = await file.read(service.max_file_bytes + 1)
        asset = service.upload_guideline(
            file.filename or "",
            content,
            content_type=file.content_type,
            uploaded_by=principal.user.user_id,
        )
        return CentralAssetResponse.from_domain(asset)


@router.put(
    "/template",
    response_model=CentralAssetResponse,
)
async def upload_template(
    principal: CurrentPrincipalDependency,
    service: CentralKnowledgeDependency,
    file: Annotated[UploadFile, File(...)],
) -> CentralAssetResponse:
    with audit_api_errors():
        content = await file.read(service.max_file_bytes + 1)
        asset = service.upload_template(
            file.filename or "",
            content,
            content_type=file.content_type,
            uploaded_by=principal.user.user_id,
        )
        return CentralAssetResponse.from_domain(asset)


@router.delete(
    "/files/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_central_asset(
    asset_id: str,
    service: CentralKnowledgeDependency,
) -> None:
    with audit_api_errors():
        service.delete_asset(asset_id)


@router.get("/files/{asset_id}/download", response_model=None)
def download_central_asset(
    asset_id: str,
    service: CentralKnowledgeDependency,
) -> FileResponse:
    with audit_api_errors():
        download = service.get_download(asset_id)
        return FileResponse(
            download.local_path,
            media_type=download.asset.content_type,
            filename=download.asset.filename,
        )
