"""Translation from audit domain errors to the stable HTTP error contract."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from fastapi import status

from app.api.errors import ApiError
from app.domain.audit import (
    ActiveJobConflictError,
    AuditIssueNotFoundError,
    AuditJobNotFoundError,
    AuditProjectNotFoundError,
    AuditStateError,
    AuditVersionNotFoundError,
    VersionConflictError,
)


@contextmanager
def audit_api_errors() -> Iterator[None]:
    try:
        yield
    except AuditProjectNotFoundError as exc:
        raise _not_found("PROJECT_NOT_FOUND", "Project", exc) from exc
    except AuditVersionNotFoundError as exc:
        raise _not_found("VERSION_NOT_FOUND", "Version", exc) from exc
    except AuditIssueNotFoundError as exc:
        raise _not_found("ISSUE_NOT_FOUND", "Issue", exc) from exc
    except AuditJobNotFoundError as exc:
        raise _not_found("JOB_NOT_FOUND", "Job", exc) from exc
    except VersionConflictError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="ROW_VERSION_CONFLICT",
            message="Issue was changed by another request. Reload it and retry.",
        ) from exc
    except ActiveJobConflictError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="ACTIVE_JOB_CONFLICT",
            message="An equivalent job is already queued or running.",
            details={"job_id": _error_value(exc)},
        ) from exc
    except AuditStateError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="INVALID_STATE",
            message=str(exc),
        ) from exc
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_REQUEST",
            message=str(exc),
        ) from exc


def _not_found(code: str, resource: str, exc: KeyError) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=code,
        message=f"{resource} not found: {_error_value(exc)}",
    )


def _error_value(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else "unknown"


def feature_unavailable(code: str, message: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        code=code,
        message=message,
    )
