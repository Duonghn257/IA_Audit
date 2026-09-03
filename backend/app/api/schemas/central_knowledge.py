"""HTTP schemas for app-wide current Guideline/template knowledge."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.application.central_knowledge_service import CentralKnowledgeSet
from app.domain.central_knowledge import CentralAssetKind, CentralAssetRecord


class CentralAssetResponse(BaseModel):
    asset_id: str
    kind: CentralAssetKind
    filename: str
    content_hash: str
    size_bytes: int
    content_type: str | None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    download_url: str

    @classmethod
    def from_domain(cls, asset: CentralAssetRecord) -> CentralAssetResponse:
        return cls(
            asset_id=asset.asset_id,
            kind=asset.kind,
            filename=asset.filename,
            content_hash=asset.content_hash,
            size_bytes=asset.size_bytes,
            content_type=asset.content_type,
            uploaded_by=asset.uploaded_by,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            download_url=(
                f"/api/v1/central-knowledge/files/{asset.asset_id}/download"
            ),
        )


class CentralKnowledgeResponse(BaseModel):
    guidelines: list[CentralAssetResponse]
    template: CentralAssetResponse | None
    ready_for_audit: bool

    @classmethod
    def from_domain(
        cls, knowledge: CentralKnowledgeSet
    ) -> CentralKnowledgeResponse:
        return cls(
            guidelines=[
                CentralAssetResponse.from_domain(item)
                for item in knowledge.guidelines
            ],
            template=(
                CentralAssetResponse.from_domain(knowledge.template)
                if knowledge.template is not None
                else None
            ),
            ready_for_audit=bool(
                knowledge.guidelines and knowledge.template is not None
            ),
        )
