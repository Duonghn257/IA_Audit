"""Manage the single current app-wide Guideline/template knowledge set."""
from __future__ import annotations

import shutil
import tempfile
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from docx import Document

from app.documents.parsers import PARSERS_BY_EXT
from app.domain.central_knowledge import (
    CentralAssetKind,
    CentralAssetNotFoundError,
    CentralAssetRecord,
    CentralKnowledgeNotReadyError,
)

_GUIDELINE_EXTENSIONS = frozenset(PARSERS_BY_EXT)
_TEMPLATE_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


@dataclass(frozen=True)
class StoredCentralAsset:
    object_key: str
    content_hash: str
    size_bytes: int


class CentralKnowledgeRepository(Protocol):
    def list_assets(self) -> list[CentralAssetRecord]: ...
    def get_asset(self, asset_id: str) -> CentralAssetRecord: ...
    def find_asset(
        self, kind: CentralAssetKind, filename: str
    ) -> CentralAssetRecord | None: ...
    def upsert_asset(
        self,
        *,
        asset_id: str,
        kind: CentralAssetKind,
        filename: str,
        object_key: str,
        content_hash: str,
        size_bytes: int,
        content_type: str | None,
        uploaded_by: str,
    ) -> CentralAssetRecord: ...
    def delete_asset(self, asset_id: str) -> CentralAssetRecord: ...


class CentralKnowledgeStorage(Protocol):
    def put_current(
        self,
        kind: CentralAssetKind,
        asset_id: str,
        filename: str,
        content: bytes,
    ) -> StoredCentralAsset: ...
    def freeze(
        self,
        job_id: str,
        assets: list[CentralAssetRecord],
    ) -> dict[str, object]: ...
    def materialize(self, object_key: str, *, suffix: str = ""): ...
    def path_for_download(self, object_key: str) -> Path: ...
    def delete(self, object_key: str) -> None: ...
    def delete_snapshot(self, job_id: str) -> None: ...


@dataclass(frozen=True)
class CentralKnowledgeSet:
    guidelines: tuple[CentralAssetRecord, ...]
    template: CentralAssetRecord | None


@dataclass(frozen=True)
class CentralAssetDownload:
    asset: CentralAssetRecord
    local_path: Path


class CentralKnowledgeService:
    def __init__(
        self,
        repository: CentralKnowledgeRepository,
        storage: CentralKnowledgeStorage,
        *,
        max_file_bytes: int = 100_000_000,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._max_file_bytes = max_file_bytes

    @property
    def max_file_bytes(self) -> int:
        return self._max_file_bytes

    def get_current(self) -> CentralKnowledgeSet:
        assets = self._repository.list_assets()
        guidelines = tuple(
            item for item in assets
            if item.kind == CentralAssetKind.GUIDELINE
        )
        template = next(
            (
                item for item in assets
                if item.kind == CentralAssetKind.TEMPLATE
            ),
            None,
        )
        return CentralKnowledgeSet(guidelines=guidelines, template=template)

    def upload_guideline(
        self,
        filename: str,
        content: bytes,
        *,
        content_type: str | None,
        uploaded_by: str,
    ) -> CentralAssetRecord:
        safe_name = _safe_filename(filename)
        suffix = PurePosixPath(safe_name).suffix.lower()
        if suffix not in _GUIDELINE_EXTENSIONS:
            raise ValueError(
                "Guideline must be a DOCX, PDF or XLSX file."
            )
        self._validate_size(content)
        _validate_guideline(safe_name, content)
        return self._store(
            CentralAssetKind.GUIDELINE,
            safe_name,
            content,
            content_type=content_type,
            uploaded_by=uploaded_by,
        )

    def upload_template(
        self,
        filename: str,
        content: bytes,
        *,
        content_type: str | None,
        uploaded_by: str,
    ) -> CentralAssetRecord:
        safe_name = _safe_filename(filename)
        if PurePosixPath(safe_name).suffix.lower() != ".docx":
            raise ValueError("Template must be a DOCX file.")
        self._validate_size(content)
        try:
            Document(BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Template DOCX cannot be opened: {exc}") from exc
        return self._store(
            CentralAssetKind.TEMPLATE,
            "template.docx",
            content,
            content_type=content_type or _TEMPLATE_CONTENT_TYPE,
            uploaded_by=uploaded_by,
        )

    def delete_asset(self, asset_id: str) -> CentralAssetRecord:
        asset = self._repository.delete_asset(asset_id)
        self._storage.delete(asset.object_key)
        return asset

    def get_download(self, asset_id: str) -> CentralAssetDownload:
        asset = self._repository.get_asset(asset_id)
        try:
            path = self._storage.path_for_download(asset.object_key)
        except FileNotFoundError as exc:
            raise CentralAssetNotFoundError(asset_id) from exc
        return CentralAssetDownload(asset=asset, local_path=path)

    def required_assets(self) -> list[CentralAssetRecord]:
        current = self.get_current()
        missing: list[str] = []
        if not current.guidelines:
            missing.append("at least one Guideline")
        template = current.template
        if template is None:
            missing.append("template.docx")
        if missing:
            raise CentralKnowledgeNotReadyError(
                "Central knowledge is not ready; upload "
                + " and ".join(missing)
                + "."
            )
        assert template is not None
        return [*current.guidelines, template]

    @staticmethod
    def manifest_for(
        assets: Sequence[CentralAssetRecord],
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "assets": [
                {
                    "asset_id": item.asset_id,
                    "kind": item.kind.value,
                    "filename": item.filename,
                    "content_hash": item.content_hash,
                    "size_bytes": item.size_bytes,
                }
                for item in sorted(
                    assets,
                    key=lambda item: (item.kind.value, item.filename),
                )
            ],
        }

    def freeze_for_job(
        self,
        job_id: str,
        assets: Sequence[CentralAssetRecord],
    ) -> dict[str, object]:
        return self._storage.freeze(job_id, list(assets))

    def materialize_for_audit(
        self,
        manifest: dict[str, object],
        workspace: Path,
        stack: ExitStack,
    ) -> None:
        entries = manifest.get("assets")
        if not isinstance(entries, list):
            raise ValueError("Frozen central knowledge manifest is invalid.")
        for raw in entries:
            if not isinstance(raw, dict):
                raise ValueError("Frozen central knowledge entry is invalid.")
            kind = CentralAssetKind(str(raw["kind"]))
            filename = str(raw["filename"])
            object_key = str(raw["object_key"])
            suffix = PurePosixPath(filename).suffix.lower()
            source = stack.enter_context(
                self._storage.materialize(object_key, suffix=suffix)
            )
            destination = (
                workspace / "Guidelines" / filename
                if kind == CentralAssetKind.GUIDELINE
                else workspace / "Output" / "template.docx"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def discard_job_snapshot(self, job_id: str) -> None:
        self._storage.delete_snapshot(job_id)

    def _store(
        self,
        kind: CentralAssetKind,
        filename: str,
        content: bytes,
        *,
        content_type: str | None,
        uploaded_by: str,
    ) -> CentralAssetRecord:
        existing = self._repository.find_asset(kind, filename)
        asset_id = existing.asset_id if existing else str(uuid4())
        stored = self._storage.put_current(
            kind, asset_id, filename, content
        )
        try:
            asset = self._repository.upsert_asset(
                asset_id=asset_id,
                kind=kind,
                filename=filename,
                object_key=stored.object_key,
                content_hash=stored.content_hash,
                size_bytes=stored.size_bytes,
                content_type=content_type,
                uploaded_by=uploaded_by,
            )
        except Exception:
            self._storage.delete(stored.object_key)
            raise
        if existing is not None and existing.object_key != stored.object_key:
            self._storage.delete(existing.object_key)
        return asset

    def _validate_size(self, content: bytes) -> None:
        if not content:
            raise ValueError("Central knowledge file must not be empty.")
        if len(content) > self._max_file_bytes:
            raise ValueError(
                f"Central knowledge file exceeds {self._max_file_bytes} bytes."
            )


def _safe_filename(filename: str) -> str:
    value = filename.strip()
    path = PurePosixPath(value.replace("\\", "/"))
    if (
        not value
        or path.is_absolute()
        or len(path.parts) != 1
        or path.name in {".", ".."}
        or path.name.startswith(("~$", ".~"))
    ):
        raise ValueError(f"Unsafe central knowledge filename: {filename!r}")
    return path.name


def _validate_guideline(filename: str, content: bytes) -> None:
    suffix = PurePosixPath(filename).suffix.lower()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        PARSERS_BY_EXT[suffix](temporary_path)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Guideline file cannot be parsed: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
