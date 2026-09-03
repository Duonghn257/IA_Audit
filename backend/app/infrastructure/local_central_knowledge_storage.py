"""Local filesystem storage for current and job-frozen central knowledge."""
from __future__ import annotations

import hashlib
import os
import shutil
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.application.central_knowledge_service import StoredCentralAsset
from app.domain.central_knowledge import CentralAssetKind, CentralAssetRecord


class LocalCentralKnowledgeStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put_current(
        self,
        kind: CentralAssetKind,
        asset_id: str,
        filename: str,
        content: bytes,
    ) -> StoredCentralAsset:
        folder = "guidelines" if kind == CentralAssetKind.GUIDELINE else "template"
        object_key = f"current/{folder}/{asset_id}/{uuid4().hex}-{filename}"
        destination = self._object_path(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.uploading"
        )
        try:
            with temporary.open("wb") as target:
                target.write(content)
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return StoredCentralAsset(
            object_key=object_key,
            content_hash=_hash_file(destination),
            size_bytes=len(content),
        )

    def freeze(
        self,
        job_id: str,
        assets: list[CentralAssetRecord],
    ) -> dict[str, object]:
        snapshot_root = self._object_path(f"snapshots/{job_id}")
        if snapshot_root.exists():
            shutil.rmtree(snapshot_root)
        entries: list[dict[str, object]] = []
        try:
            for asset in assets:
                source = self._object_path(asset.object_key)
                if not source.is_file() or _hash_file(source) != asset.content_hash:
                    raise ValueError(
                        "Central knowledge changed while Audit was starting: "
                        f"{asset.filename}"
                    )
                folder = (
                    "Guidelines"
                    if asset.kind == CentralAssetKind.GUIDELINE
                    else "Output"
                )
                filename = (
                    asset.filename
                    if asset.kind == CentralAssetKind.GUIDELINE
                    else "template.docx"
                )
                object_key = f"snapshots/{job_id}/{folder}/{filename}"
                destination = self._object_path(object_key)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                entries.append(
                    {
                        "asset_id": asset.asset_id,
                        "kind": asset.kind.value,
                        "filename": filename,
                        "object_key": object_key,
                        "content_hash": asset.content_hash,
                        "size_bytes": asset.size_bytes,
                    }
                )
        except Exception:
            shutil.rmtree(snapshot_root, ignore_errors=True)
            raise
        return {"schema_version": 1, "assets": entries}

    @contextmanager
    def materialize(self, object_key: str, *, suffix: str = ""):
        source = self._object_path(object_key)
        if not source.is_file():
            raise FileNotFoundError(object_key)
        materialized = source
        if suffix:
            materialized = source.with_name(f".{source.name}.{uuid4().hex}{suffix}")
            try:
                os.link(source, materialized)
            except OSError:
                shutil.copy2(source, materialized)
        try:
            yield materialized
        finally:
            if materialized != source:
                materialized.unlink(missing_ok=True)

    def path_for_download(self, object_key: str) -> Path:
        path = self._object_path(object_key)
        if not path.is_file():
            raise FileNotFoundError(object_key)
        return path

    def delete(self, object_key: str) -> None:
        path = self._object_path(object_key)
        path.unlink(missing_ok=True)
        parent = path.parent
        if parent != self._root:
            try:
                parent.rmdir()
            except OSError:
                pass

    def delete_snapshot(self, job_id: str) -> None:
        shutil.rmtree(
            self._object_path(f"snapshots/{job_id}"),
            ignore_errors=True,
        )

    def _object_path(self, object_key: str) -> Path:
        relative = _safe_relative_path(object_key)
        path = self._root.joinpath(*relative.parts).resolve()
        if self._root not in path.parents:
            raise ValueError(f"Unsafe central knowledge key: {object_key!r}")
        return path


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value.replace("\\", "/").strip())
    if (
        not value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"Unsafe central knowledge key: {value!r}")
    return path


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
