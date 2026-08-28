"""Errors and state enums for the UAT audit workspace."""
from __future__ import annotations

from enum import StrEnum


class UploadSessionNotFoundError(KeyError):
    """Raised when an upload session does not exist."""


class UploadFileNotFoundError(KeyError):
    """Raised when a staged upload file does not exist."""


class AuditProjectNotFoundError(KeyError):
    """Raised when a UAT audit project does not exist."""


class AuditVersionNotFoundError(KeyError):
    """Raised when an audit version does not exist."""


class AuditIssueNotFoundError(KeyError):
    """Raised when an issue does not exist."""


class AuditJobNotFoundError(KeyError):
    """Raised when a durable job does not exist."""


class AuditOutputNotFoundError(KeyError):
    """Raised when a generated output revision does not exist."""


class DuplicateProjectNameError(ValueError):
    """Raised when a project name is already in use."""


class AuditStateError(RuntimeError):
    """Raised when a workflow transition is invalid."""


class VersionConflictError(RuntimeError):
    """Raised when optimistic concurrency detects a stale issue update."""


class ActiveJobConflictError(RuntimeError):
    """Raised when an equivalent active job already exists."""


class JobNotRetryableError(RuntimeError):
    """Raised when a job is not in a retryable terminal state."""


class SourceNotReadyError(ValueError):
    """Raised when immutable source cannot satisfy discovery input."""


class AuditPreflightError(ValueError):
    """Raised when an Audit job cannot freeze a valid issue input."""


class UploadSessionState(StrEnum):
    UPLOADING = "UPLOADING"
    VALIDATING = "VALIDATING"
    READY_TO_CREATE = "READY_TO_CREATE"
    INVALID = "INVALID"
    PROMOTED = "PROMOTED"
    EXPIRED = "EXPIRED"


class LogicalRole(StrEnum):
    SCOPE = "SCOPE"
    RISK_CONTEXT = "RISK_CONTEXT"
    EVIDENCE = "EVIDENCE"
    CRITERIA = "CRITERIA"
    CONTEXT = "CONTEXT"


class ProjectState(StrEnum):
    READY_FOR_DISCOVERY = "READY_FOR_DISCOVERY"
    CANDIDATES_AVAILABLE = "CANDIDATES_AVAILABLE"
    OUTPUT_AVAILABLE = "OUTPUT_AVAILABLE"


class AuditVersionState(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATES_READY = "CANDIDATES_READY"
    AUDITING = "AUDITING"
    DOCX_READY = "DOCX_READY"
    STALE_OUTPUT = "STALE_OUTPUT"


class IssueOrigin(StrEnum):
    AI_DISCOVERED = "AI_DISCOVERED"
    MANUAL = "MANUAL"


class IssueStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    REJECTED = "REJECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class RiskCategory(StrEnum):
    COMPLIANCE = "Compliance"
    OPERATIONAL = "Operational"
    STRATEGIC = "Strategic"
    FINANCIAL = "Financial"


class SourceRefKind(StrEnum):
    EVIDENCE = "EVIDENCE"
    CRITERIA = "CRITERIA"


class JobType(StrEnum):
    DISCOVERY = "DISCOVERY"
    AUDIT = "AUDIT"


class JobState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"

    @property
    def is_active(self) -> bool:
        return self in {JobState.QUEUED, JobState.RUNNING}


class OutputStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
