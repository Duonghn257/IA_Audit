"""Compatibility facade for the split UAT persistence repositories.

New application services should depend on the smallest repository that matches
their responsibility. The facade is retained while the API layer is migrated.
"""
from app.infrastructure.audit_intake_repository import SqlAlchemyAuditIntakeRepository
from app.infrastructure.audit_job_repository import SqlAlchemyAuditJobRepository
from app.infrastructure.audit_models import SourceDocumentModel
from app.infrastructure.audit_workspace_repository import SqlAlchemyAuditWorkspaceRepository


class SqlAlchemyAuditRepository(
    SqlAlchemyAuditIntakeRepository,
    SqlAlchemyAuditWorkspaceRepository,
    SqlAlchemyAuditJobRepository,
):
    """Temporary aggregate preserving the original repository import path."""


__all__ = [
    "SourceDocumentModel",
    "SqlAlchemyAuditIntakeRepository",
    "SqlAlchemyAuditJobRepository",
    "SqlAlchemyAuditRepository",
    "SqlAlchemyAuditWorkspaceRepository",
]
