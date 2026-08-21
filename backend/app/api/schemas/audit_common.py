"""Shared request and response fields for audit workspace APIs."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.domain.audit import SourceRefKind, SourceReferenceInput, SourceReferenceRecord


class SourceReferenceRequest(BaseModel):
    ref_kind: SourceRefKind
    document_id: str
    unit_id: str | None = None
    location: dict[str, Any] = Field(default_factory=dict)
    quote: str | None = None

    def to_domain(self) -> SourceReferenceInput:
        from uuid import uuid4

        return SourceReferenceInput(
            reference_id=str(uuid4()),
            ref_kind=self.ref_kind,
            document_id=self.document_id,
            unit_id=self.unit_id,
            location=self.location,
            quote=self.quote,
        )


class SourceReferenceResponse(BaseModel):
    reference_id: str
    ref_kind: SourceRefKind
    document_id: str
    unit_id: str | None
    location: dict[str, Any]
    quote: str | None

    @classmethod
    def from_domain(cls, value: SourceReferenceRecord) -> "SourceReferenceResponse":
        return cls(**value.__dict__)
