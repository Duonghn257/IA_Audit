"""Schemas for issue review and manual issue editing."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.audit_common import SourceReferenceRequest, SourceReferenceResponse
from app.domain.audit import (
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    RiskCategory,
    compatibility_reference_lists,
)


class CreateManualIssueRequest(BaseModel):
    observed_gap: str = Field(min_length=1)
    title_hint: str | None = None
    evidence_summary: str | None = None
    risk_category: RiskCategory | None = None
    status: IssueStatus = IssueStatus.DRAFT
    source_refs: list[SourceReferenceRequest] = Field(default_factory=list)


class UpdateIssueRequest(BaseModel):
    row_version: int = Field(ge=1)
    observed_gap: str = Field(min_length=1)
    title_hint: str | None = None
    evidence_summary: str | None = None
    risk_category: RiskCategory | None = None
    source_refs: list[SourceReferenceRequest] = Field(default_factory=list)


class IssueDispositionRequest(BaseModel):
    row_version: int = Field(ge=1)
    status: IssueStatus


class IssueResponse(BaseModel):
    issue_id: str
    project_version_id: str
    origin: IssueOrigin
    status: IssueStatus
    observed_gap: str
    title_hint: str | None
    evidence_summary: str | None
    evidence_refs: list[str] = Field(deprecated=True)
    sop_refs: list[str] = Field(deprecated=True)
    risk_category: RiskCategory | None
    confidence: float | None
    validation_flags: list[str]
    row_version: int
    source_refs: list[SourceReferenceResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, value: IssueRecord) -> IssueResponse:
        evidence_refs = value.evidence_refs
        sop_refs = value.sop_refs
        if value.source_refs:
            evidence_refs, sop_refs = compatibility_reference_lists(
                value.source_refs
            )
        return cls(
            issue_id=value.issue_id,
            project_version_id=value.project_version_id,
            origin=value.origin,
            status=value.status,
            observed_gap=value.observed_gap,
            title_hint=value.title_hint,
            evidence_summary=value.evidence_summary,
            evidence_refs=list(evidence_refs),
            sop_refs=list(sop_refs),
            risk_category=value.risk_category,
            confidence=value.confidence,
            validation_flags=value.validation_flags,
            row_version=value.row_version,
            source_refs=[SourceReferenceResponse.from_domain(item) for item in value.source_refs],
            created_at=value.created_at,
            updated_at=value.updated_at,
        )
