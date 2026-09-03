"""Domain records for app-wide Guideline and DOCX template knowledge."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CentralAssetKind(StrEnum):
    GUIDELINE = "GUIDELINE"
    TEMPLATE = "TEMPLATE"


class CentralAssetNotFoundError(KeyError):
    """Raised when a central knowledge file does not exist."""


class CentralKnowledgeNotReadyError(ValueError):
    """Raised when Audit cannot freeze the required central knowledge."""


@dataclass(frozen=True)
class CentralAssetRecord:
    asset_id: str
    kind: CentralAssetKind
    filename: str
    object_key: str
    content_hash: str
    size_bytes: int
    content_type: str | None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
