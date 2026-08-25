"""Persistence operations for staging uploads and project promotion."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.audit import (
    AuditProjectRecord,
    AuditStateError,
    DuplicateProjectNameError,
    ProjectState,
    ProjectVersionRecord,
    UploadFileInput,
    UploadFileNotFoundError,
    UploadFileRecord,
    UploadFileValidation,
    UploadSessionRecord,
    UploadSessionState,
)
from app.infrastructure.audit_models import (
    ProjectVersionModel,
    SourceDocumentModel,
    SourceSnapshotModel,
    UploadFileModel,
    UploadSessionModel,
)
from app.infrastructure.audit_persistence import (
    get_upload_session,
    require_upload_state,
    to_project_record,
    to_upload_file_record,
    to_upload_session_record,
    to_version_record,
    utcnow,
)
from app.infrastructure.project_repository import ProjectModel


class SqlAlchemyAuditIntakeRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def create_upload_session(
        self,
        *,
        session_id: str,
        files: Sequence[UploadFileInput],
        expires_at: datetime,
        actor_id: str = "uat_shared_user",
        actor_label: str = "UAT shared user",
        actor_type: str = "UAT_SHARED",
    ) -> UploadSessionRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            model = UploadSessionModel(
                session_id=session_id,
                state=UploadSessionState.UPLOADING.value,
                actor_id=actor_id,
                actor_label=actor_label,
                actor_type=actor_type,
                created_at=now,
                expires_at=expires_at,
            )
            session.add(model)
            session.add_all(
                UploadFileModel(
                    file_id=file.file_id,
                    session_id=session_id,
                    relative_path=file.relative_path,
                    size_bytes=file.size_bytes,
                    content_type=file.content_type,
                    staging_object_key=file.staging_object_key,
                    modified_at=file.modified_at,
                )
                for file in files
            )
        return to_upload_session_record(model)

    def get_upload_session(self, session_id: str) -> UploadSessionRecord:
        with self._sessions() as session:
            return to_upload_session_record(
                get_upload_session(session, session_id)
            )

    def list_upload_files(
        self, session_id: str
    ) -> list[UploadFileRecord]:
        with self._sessions() as session:
            get_upload_session(session, session_id)
            files = session.scalars(
                select(UploadFileModel)
                .where(UploadFileModel.session_id == session_id)
                .order_by(
                    UploadFileModel.relative_path,
                    UploadFileModel.file_id,
                )
            ).all()
            return [to_upload_file_record(file) for file in files]

    def get_upload_file(
        self, session_id: str, file_id: str
    ) -> UploadFileRecord:
        with self._sessions() as session:
            get_upload_session(session, session_id)
            file = session.scalars(
                select(UploadFileModel).where(
                    UploadFileModel.file_id == file_id,
                    UploadFileModel.session_id == session_id,
                )
            ).first()
            if file is None:
                raise UploadFileNotFoundError(file_id)
            return to_upload_file_record(file)

    def mark_upload_file_uploaded(
        self, session_id: str, file_id: str
    ) -> UploadFileRecord:
        with self._sessions.begin() as session:
            upload = get_upload_session(session, session_id, lock=True)
            require_upload_state(
                upload,
                {
                    UploadSessionState.UPLOADING,
                    UploadSessionState.INVALID,
                },
            )
            file = session.scalars(
                select(UploadFileModel)
                .where(
                    UploadFileModel.file_id == file_id,
                    UploadFileModel.session_id == session_id,
                )
                .with_for_update()
            ).first()
            if file is None:
                raise UploadFileNotFoundError(file_id)
            file.upload_status = "UPLOADED"
            file.content_hash = None
            file.logical_role = None
            file.readability_status = None
            file.validation_message = None
            if upload.state == UploadSessionState.INVALID.value:
                upload.state = UploadSessionState.UPLOADING.value
                upload.validation_report = None
        return to_upload_file_record(file)

    def complete_upload_validation(
        self,
        session_id: str,
        *,
        validation_report: dict[str, Any],
        files: Sequence[UploadFileValidation],
        valid: bool,
    ) -> UploadSessionRecord:
        with self._sessions.begin() as session:
            model = get_upload_session(session, session_id, lock=True)
            require_upload_state(
                model,
                {
                    UploadSessionState.UPLOADING,
                    UploadSessionState.VALIDATING,
                },
            )
            validations = {entry.file_id: entry for entry in files}
            for file in model.files:
                entry = validations.get(file.file_id)
                if entry is None:
                    raise AuditStateError(
                        f"Upload file {file.file_id} is missing validation."
                    )
                file.content_hash = entry.content_hash
                file.logical_role = entry.logical_role.value
                file.readability_status = entry.readability_status
                file.validation_message = entry.validation_message
            model.validation_report = validation_report
            model.state = (
                UploadSessionState.READY_TO_CREATE.value
                if valid
                else UploadSessionState.INVALID.value
            )
        return to_upload_session_record(model)

    def promote_upload_session(
        self,
        session_id: str,
        *,
        project_id: str,
        source_snapshot_id: str,
        version_id: str,
        name: str,
        manifest_hash: str,
        source_object_prefix: str,
        source_object_keys: dict[str, str] | None = None,
    ) -> tuple[AuditProjectRecord, ProjectVersionRecord]:
        now = utcnow()
        try:
            with self._sessions.begin() as session:
                upload = get_upload_session(
                    session, session_id, lock=True
                )
                require_upload_state(
                    upload, {UploadSessionState.READY_TO_CREATE}
                )
                duplicate = session.scalar(
                    select(ProjectModel.project_id).where(
                        ProjectModel.name == name
                    )
                )
                if duplicate is not None:
                    raise DuplicateProjectNameError(name)
                project = ProjectModel(
                    project_id=project_id,
                    name=name,
                    source_type="LOCAL_UPLOAD",
                    status=ProjectState.READY_FOR_DISCOVERY.value,
                    current_activity="Source snapshot ready for discovery",
                    created_at=now,
                    updated_at=now,
                )
                snapshot = SourceSnapshotModel(
                    snapshot_id=source_snapshot_id,
                    project_id=project_id,
                    manifest_hash=manifest_hash,
                    manifest=upload.validation_report or {},
                    source_object_prefix=source_object_prefix,
                    promoted_at=now,
                )
                version = ProjectVersionModel(
                    version_id=version_id,
                    project_id=project_id,
                    sequence_no=1,
                    label="v0.1",
                    state="DRAFT",
                    issue_revision=0,
                    created_at=now,
                    updated_at=now,
                )
                # These models intentionally do not expose ORM relationships to
                # ProjectModel. Flush each FK level explicitly so PostgreSQL does
                # not insert a version/snapshot before its parent project during
                # the lazy-load autoflush triggered by ``upload.files`` below.
                session.add(project)
                session.flush([project])
                session.add_all([snapshot, version])
                session.flush([snapshot, version])
                for file in upload.files:
                    if (
                        not file.content_hash
                        or not file.logical_role
                        or file.readability_status != "READABLE"
                    ):
                        raise AuditStateError(
                            "All uploaded files must pass validation "
                            "before promotion."
                        )
                    object_key = (
                        source_object_keys.get(
                            file.file_id, file.staging_object_key
                        )
                        if source_object_keys
                        else file.staging_object_key
                    )
                    session.add(
                        SourceDocumentModel(
                            document_id=str(uuid4()),
                            snapshot_id=source_snapshot_id,
                            relative_path=file.relative_path,
                            logical_role=file.logical_role,
                            original_object_key=object_key,
                            content_hash=file.content_hash,
                            size_bytes=file.size_bytes,
                            content_type=file.content_type,
                            upload_status=file.upload_status,
                        )
                    )
                upload.state = UploadSessionState.PROMOTED.value
                upload.promoted_at = now
                session.flush()
        except IntegrityError as exc:
            if (
                "projects" in str(exc).lower()
                and "name" in str(exc).lower()
            ):
                raise DuplicateProjectNameError(name) from exc
            raise
        return (
            to_project_record(project, snapshot, 2),
            to_version_record(version),
        )

    def delete_upload_session(self, session_id: str) -> None:
        with self._sessions.begin() as session:
            upload = get_upload_session(session, session_id, lock=True)
            if upload.state == UploadSessionState.PROMOTED.value:
                raise AuditStateError(
                    "A promoted upload session cannot be discarded."
                )
            session.delete(upload)
