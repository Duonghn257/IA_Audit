"""Application service for UAT upload sessions and immutable source intake."""
from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from app.documents.parsers import PARSERS_BY_EXT
from app.domain.audit import (
    AuditProjectRecord,
    AuditStateError,
    LogicalRole,
    ProjectVersionRecord,
    UploadFileInput,
    UploadFileRecord,
    UploadFileValidation,
    UploadSessionNotFoundError,
    UploadSessionRecord,
    UploadSessionState,
)

_SUPPORTED_EXTENSIONS = frozenset(PARSERS_BY_EXT)
_ROLE_FOLDERS = {
    "AWP": LogicalRole.SCOPE,
    "APM": LogicalRole.RISK_CONTEXT,
    "Process Understanding": LogicalRole.EVIDENCE,
    "Process SOP": LogicalRole.CRITERIA,
}
_REQUIRED_FOLDERS = frozenset(_ROLE_FOLDERS)
_REQUIRED_ROLES = (
    LogicalRole.SCOPE,
    LogicalRole.RISK_CONTEXT,
    LogicalRole.EVIDENCE,
    LogicalRole.CRITERIA,
)


@dataclass(frozen=True)
class UploadFileDescriptor:
    relative_path: str
    size_bytes: int
    content_type: str | None = None
    modified_at: datetime | None = None


@dataclass(frozen=True)
class StoredUpload:
    size_bytes: int
    content_hash: str


@dataclass(frozen=True)
class PromotedSource:
    object_prefix: str
    object_keys: dict[str, str]


@dataclass(frozen=True)
class UploadFileView:
    file: UploadFileRecord
    upload_method: str
    upload_url: str
    required_headers: dict[str, str]


@dataclass(frozen=True)
class UploadSessionView:
    session: UploadSessionRecord
    files: tuple[UploadFileView, ...]
    allowed_actions: tuple[str, ...]
    action_reasons: dict[str, str]


@dataclass(frozen=True)
class PromotedProject:
    project: AuditProjectRecord
    version: ProjectVersionRecord


class AuditIntakeRepository(Protocol):
    def create_upload_session(
        self,
        *,
        session_id: str,
        files: Sequence[UploadFileInput],
        expires_at: datetime,
        actor_id: str = "uat_shared_user",
        actor_label: str = "UAT shared user",
        actor_type: str = "UAT_SHARED",
    ) -> UploadSessionRecord: ...

    def get_upload_session(self, session_id: str) -> UploadSessionRecord: ...

    def list_upload_files(self, session_id: str) -> list[UploadFileRecord]: ...

    def get_upload_file(
        self, session_id: str, file_id: str
    ) -> UploadFileRecord: ...

    def mark_upload_file_uploaded(
        self, session_id: str, file_id: str
    ) -> UploadFileRecord: ...

    def complete_upload_validation(
        self,
        session_id: str,
        *,
        validation_report: dict[str, object],
        files: Sequence[UploadFileValidation],
        valid: bool,
    ) -> UploadSessionRecord: ...

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
    ) -> tuple[AuditProjectRecord, ProjectVersionRecord]: ...

    def delete_upload_session(self, session_id: str) -> None: ...


class AuditIntakeStorage(Protocol):
    def staging_key(self, session_id: str, file_id: str) -> str: ...

    def upload_url(self, session_id: str, file_id: str) -> str: ...

    async def put_upload(
        self,
        object_key: str,
        chunks: AsyncIterable[bytes],
        *,
        expected_size: int,
    ) -> StoredUpload: ...

    def inspect(self, object_key: str) -> StoredUpload | None: ...

    def materialize(
        self, object_key: str, *, suffix: str = ""
    ) -> AbstractContextManager[Path]: ...

    def promote_uploads(
        self,
        session_id: str,
        project_id: str,
        files: Sequence[UploadFileRecord],
    ) -> PromotedSource: ...

    def discard_upload(self, session_id: str) -> None: ...

    def delete_project_source(self, project_id: str) -> None: ...


class AuditIntakeService:
    def __init__(
        self,
        repository: AuditIntakeRepository,
        storage: AuditIntakeStorage,
        *,
        max_files: int = 20,
        max_total_bytes: int = 100_000_000,
        session_ttl_hours: int = 24,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._max_files = max_files
        self._max_total_bytes = max_total_bytes
        self._session_ttl = timedelta(hours=session_ttl_hours)

    def create_session(
        self,
        files: Sequence[UploadFileDescriptor],
        *,
        actor_id: str = "uat_shared_user",
        actor_label: str = "UAT shared user",
        actor_type: str = "UAT_SHARED",
    ) -> UploadSessionView:
        normalized = self._validate_manifest(files)
        session_id = str(uuid4())
        inputs: list[UploadFileInput] = []
        for descriptor in normalized:
            file_id = str(uuid4())
            inputs.append(
                UploadFileInput(
                    file_id=file_id,
                    relative_path=descriptor.relative_path,
                    size_bytes=descriptor.size_bytes,
                    content_type=descriptor.content_type,
                    staging_object_key=self._storage.staging_key(
                        session_id, file_id
                    ),
                    modified_at=descriptor.modified_at,
                )
            )
        session = self._repository.create_upload_session(
            session_id=session_id,
            files=inputs,
            expires_at=datetime.now(timezone.utc) + self._session_ttl,
            actor_id=actor_id,
            actor_label=actor_label,
            actor_type=actor_type,
        )
        return self._view(session)

    def get_session(
        self,
        session_id: str,
        *,
        actor_id: str | None = None,
    ) -> UploadSessionView:
        return self._view(self._session_for_actor(session_id, actor_id))

    async def upload_file(
        self,
        session_id: str,
        file_id: str,
        chunks: AsyncIterable[bytes],
        *,
        actor_id: str | None = None,
    ) -> UploadFileView:
        session = self._active_session(session_id, actor_id)
        if session.state not in {
            UploadSessionState.UPLOADING,
            UploadSessionState.INVALID,
        }:
            raise AuditStateError(
                f"Upload session {session_id} no longer accepts files."
            )
        file = self._repository.get_upload_file(session_id, file_id)
        await self._storage.put_upload(
            file.staging_object_key,
            chunks,
            expected_size=file.size_bytes,
        )
        uploaded = self._repository.mark_upload_file_uploaded(
            session_id, file_id
        )
        return self._file_view(uploaded)

    def validate_session(
        self,
        session_id: str,
        *,
        actor_id: str | None = None,
    ) -> UploadSessionView:
        self._active_session(session_id, actor_id)
        files = self._repository.list_upload_files(session_id)
        validations: list[UploadFileValidation] = []
        errors: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        role_summary = {role.value: 0 for role in _REQUIRED_ROLES}

        for file in files:
            role = _logical_role(file.relative_path)
            stored = self._storage.inspect(file.staging_object_key)
            readability = "READABLE"
            message: str | None = None
            content_hash = "sha256:missing"
            if file.upload_status != "UPLOADED" or stored is None:
                readability = "MISSING"
                message = "File content has not been uploaded."
                errors.append(
                    _validation_message(
                        "UPLOAD_INCOMPLETE", message, file, blocking=True
                    )
                )
            elif stored.size_bytes != file.size_bytes:
                readability = "SIZE_MISMATCH"
                message = (
                    f"Uploaded size {stored.size_bytes} does not match "
                    f"declared size {file.size_bytes}."
                )
                content_hash = stored.content_hash
                errors.append(
                    _validation_message(
                        "FILE_SIZE_MISMATCH", message, file, blocking=True
                    )
                )
            else:
                content_hash = stored.content_hash
                suffix = PurePosixPath(file.relative_path).suffix.lower()
                parser = PARSERS_BY_EXT[suffix]
                try:
                    with self._storage.materialize(
                        file.staging_object_key,
                        suffix=suffix,
                    ) as local_path:
                        parser(local_path)
                except Exception as exc:  # noqa: BLE001
                    readability = "UNREADABLE"
                    message = f"File cannot be parsed: {exc}"
                    errors.append(
                        _validation_message(
                            "FILE_UNREADABLE", message, file, blocking=True
                        )
                    )

            if role.value in role_summary and readability == "READABLE":
                role_summary[role.value] += 1
            elif role == LogicalRole.CONTEXT:
                warnings.append(
                    _validation_message(
                        "UNMAPPED_LOGICAL_ROLE",
                        "File is retained as context but is not a required UAT role.",
                        file,
                        blocking=False,
                    )
                )
            validations.append(
                UploadFileValidation(
                    file_id=file.file_id,
                    content_hash=content_hash,
                    logical_role=role,
                    readability_status=readability,
                    validation_message=message,
                )
            )

        for role in _REQUIRED_ROLES:
            if role_summary[role.value] == 0:
                errors.append(
                    {
                        "code": "REQUIRED_ROLE_MISSING",
                        "message": (
                            f"No readable file was found for role {role.value}."
                        ),
                        "file_id": None,
                        "relative_path": None,
                        "blocking": True,
                        "details": {"logical_role": role.value},
                    }
                )

        report: dict[str, object] = {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "role_summary": role_summary,
        }
        session = self._repository.complete_upload_validation(
            session_id,
            validation_report=report,
            files=validations,
            valid=not errors,
        )
        return self._view(session)

    def promote_session(
        self,
        session_id: str,
        name: str,
        *,
        actor_id: str | None = None,
    ) -> PromotedProject:
        session = self._active_session(session_id, actor_id)
        if session.state != UploadSessionState.READY_TO_CREATE:
            raise AuditStateError(
                f"Upload session {session_id} is not ready to create a project."
            )
        project_name = name.strip()
        if not project_name:
            raise ValueError("Project name must not be empty.")

        files = self._repository.list_upload_files(session_id)
        project_id = str(uuid4())
        promoted = self._storage.promote_uploads(
            session_id, project_id, files
        )
        manifest_hash = _manifest_hash(files)
        try:
            project, version = self._repository.promote_upload_session(
                session_id,
                project_id=project_id,
                source_snapshot_id=str(uuid4()),
                version_id=str(uuid4()),
                name=project_name,
                manifest_hash=manifest_hash,
                source_object_prefix=promoted.object_prefix,
                source_object_keys=promoted.object_keys,
            )
        except Exception:
            self._storage.delete_project_source(project_id)
            raise
        self._storage.discard_upload(session_id)
        return PromotedProject(project, version)

    def discard_session(
        self,
        session_id: str,
        *,
        actor_id: str | None = None,
    ) -> None:
        self._session_for_actor(session_id, actor_id)
        self._repository.delete_upload_session(session_id)
        self._storage.discard_upload(session_id)

    def _active_session(
        self,
        session_id: str,
        actor_id: str | None = None,
    ) -> UploadSessionRecord:
        session = self._session_for_actor(session_id, actor_id)
        if session.expires_at <= datetime.now(timezone.utc):
            raise AuditStateError(
                f"Upload session {session_id} has expired."
            )
        return session

    def _session_for_actor(
        self,
        session_id: str,
        actor_id: str | None,
    ) -> UploadSessionRecord:
        session = self._repository.get_upload_session(session_id)
        if actor_id is not None and session.actor_id != actor_id:
            raise UploadSessionNotFoundError(session_id)
        return session

    def _view(self, session: UploadSessionRecord) -> UploadSessionView:
        files = tuple(
            self._file_view(file)
            for file in self._repository.list_upload_files(
                session.session_id
            )
        )
        actions: list[str] = ["DISCARD"]
        reasons: dict[str, str] = {}
        if session.state == UploadSessionState.UPLOADING:
            actions.extend(["UPLOAD_FILES", "VALIDATE"])
            reasons["CREATE_PROJECT"] = "Validation has not passed."
        elif session.state == UploadSessionState.READY_TO_CREATE:
            actions.append("CREATE_PROJECT")
        elif session.state == UploadSessionState.INVALID:
            actions.extend(["UPLOAD_FILES", "VALIDATE"])
            reasons["CREATE_PROJECT"] = "Blocking validation errors exist."
        elif session.state == UploadSessionState.PROMOTED:
            actions = []
        return UploadSessionView(
            session=session,
            files=files,
            allowed_actions=tuple(actions),
            action_reasons=reasons,
        )

    def _file_view(self, file: UploadFileRecord) -> UploadFileView:
        headers = {"Content-Type": file.content_type or "application/octet-stream"}
        return UploadFileView(
            file=file,
            upload_method="PUT",
            upload_url=self._storage.upload_url(
                file.session_id, file.file_id
            ),
            required_headers=headers,
        )

    def _validate_manifest(
        self, files: Sequence[UploadFileDescriptor]
    ) -> list[UploadFileDescriptor]:
        if not files:
            raise ValueError("The uploaded folder is empty.")
        normalized: list[UploadFileDescriptor] = []
        seen: set[str] = set()
        total_bytes = 0
        for file in files:
            path = _normalize_relative_path(file.relative_path)
            suffix = PurePosixPath(path).suffix.lower()
            filename = PurePosixPath(path).name
            if (
                suffix not in _SUPPORTED_EXTENSIONS
                or filename.startswith(("~$", ".~"))
            ):
                continue
            if _project_folder(path) is None:
                continue
            if file.size_bytes <= 0:
                raise ValueError(f"File {path} must not be empty.")
            if path in seen:
                raise ValueError(f"Duplicate relative path: {path}")
            seen.add(path)
            total_bytes += file.size_bytes
            normalized.append(
                UploadFileDescriptor(
                    relative_path=path,
                    size_bytes=file.size_bytes,
                    content_type=file.content_type,
                    modified_at=file.modified_at,
                )
            )
        if not normalized:
            raise ValueError(
                "The selected folder contains no supported DOCX, PDF or XLSX files."
            )
        if len(normalized) > self._max_files:
            raise ValueError(
                f"Folder contains more than {self._max_files} supported files."
            )
        if total_bytes > self._max_total_bytes:
            raise ValueError(
                f"Folder exceeds the {self._max_total_bytes} byte limit."
            )
        return normalized


def _normalize_relative_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"Unsafe relative path: {raw_path!r}")
    return path.as_posix()


def _project_folder(relative_path: str) -> tuple[str, str | None] | None:
    parts = PurePosixPath(relative_path).parts
    if len(parts) < 2:
        raise ValueError(
            f"File {relative_path} must be inside one of the required audit folders."
        )
    if parts[0] in _REQUIRED_FOLDERS:
        return parts[0], None
    if len(parts) >= 3 and parts[1] in _REQUIRED_FOLDERS:
        return parts[1], parts[0]
    candidate = parts[1] if len(parts) >= 3 else parts[0]
    expected_by_casefold = {
        folder.casefold(): folder for folder in _REQUIRED_FOLDERS
    }
    expected = expected_by_casefold.get(candidate.casefold())
    if expected is not None:
        raise ValueError(
            f"Invalid audit folder {candidate!r} in {relative_path}; "
            f"folder name must match {expected!r} exactly."
        )
    return None


def _logical_role(relative_path: str) -> LogicalRole:
    for part in PurePosixPath(relative_path).parts[:-1]:
        role = _ROLE_FOLDERS.get(part)
        if role is not None:
            return role
    return LogicalRole.CONTEXT


def _validation_message(
    code: str,
    message: str,
    file: UploadFileRecord,
    *,
    blocking: bool,
) -> dict[str, object]:
    return {
        "code": code,
        "message": message,
        "file_id": file.file_id,
        "relative_path": file.relative_path,
        "blocking": blocking,
        "details": {},
    }


def _manifest_hash(files: Sequence[UploadFileRecord]) -> str:
    payload = [
        {
            "relative_path": file.relative_path,
            "content_hash": file.content_hash,
            "logical_role": (
                file.logical_role.value if file.logical_role else None
            ),
        }
        for file in sorted(files, key=lambda item: item.relative_path)
    ]
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
