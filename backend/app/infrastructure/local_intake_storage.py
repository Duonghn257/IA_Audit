"""Local filesystem adapter for the UAT upload-session storage port."""
from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import AsyncIterable, Sequence
from contextlib import nullcontext
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import uuid4

from app.application.audit_intake_service import (
    PromotedSource,
    StoredUpload,
)
from app.domain.audit import UploadFileRecord


class LocalAuditIntakeStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def staging_key(self, session_id: str, file_id: str) -> str:
        return f"staging/{session_id}/files/{file_id}"

    def upload_url(self, session_id: str, file_id: str) -> str:
        return (
            "/api/v1/upload-sessions/"
            f"{quote(session_id, safe='')}/files/{quote(file_id, safe='')}"
        )

    async def put_upload(
        self,
        object_key: str,
        chunks: AsyncIterable[bytes],
        *,
        expected_size: int,
    ) -> StoredUpload:
        destination = self._object_path(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.uploading"
        )
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("wb") as target:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > expected_size:
                        raise ValueError(
                            "Uploaded content exceeds the declared file size."
                        )
                    digest.update(chunk)
                    target.write(chunk)
            if size != expected_size:
                raise ValueError(
                    f"Uploaded size {size} does not match declared "
                    f"size {expected_size}."
                )
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return StoredUpload(
            size_bytes=size,
            content_hash=f"sha256:{digest.hexdigest()}",
        )

    def inspect(self, object_key: str) -> StoredUpload | None:
        path = self._object_path(object_key)
        if not path.is_file():
            return None
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        return StoredUpload(
            size_bytes=size,
            content_hash=f"sha256:{digest.hexdigest()}",
        )

    def materialize(self, object_key: str):
        path = self._object_path(object_key)
        if not path.is_file():
            raise FileNotFoundError(object_key)
        return nullcontext(path)

    def promote_uploads(
        self,
        session_id: str,
        project_id: str,
        files: Sequence[UploadFileRecord],
    ) -> PromotedSource:
        source_root = self._object_path(
            f"projects/{project_id}/source"
        )
        if source_root.exists():
            raise ValueError(
                f"Source snapshot already exists for project {project_id}."
            )
        object_keys: dict[str, str] = {}
        try:
            for file in files:
                source = self._object_path(file.staging_object_key)
                if not source.is_file():
                    raise ValueError(
                        f"Uploaded object is missing: {file.relative_path}"
                    )
                relative = _safe_relative_path(file.relative_path)
                object_key = (
                    f"projects/{project_id}/source/{relative.as_posix()}"
                )
                destination = self._object_path(object_key)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                object_keys[file.file_id] = object_key
        except Exception:
            shutil.rmtree(source_root, ignore_errors=True)
            raise
        return PromotedSource(
            object_prefix=f"projects/{project_id}/source",
            object_keys=object_keys,
        )

    def discard_upload(self, session_id: str) -> None:
        staging_root = self._object_path(f"staging/{session_id}")
        shutil.rmtree(staging_root, ignore_errors=True)

    def delete_project_source(self, project_id: str) -> None:
        source_root = self._object_path(
            f"projects/{project_id}/source"
        )
        shutil.rmtree(source_root, ignore_errors=True)

    def _object_path(self, object_key: str) -> Path:
        relative = _safe_relative_path(object_key)
        path = self._root.joinpath(*relative.parts).resolve()
        if self._root not in path.parents:
            raise ValueError(f"Unsafe object key: {object_key!r}")
        return path


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value.replace("\\", "/").strip())
    if (
        not value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path
