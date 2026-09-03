"""SQLAlchemy persistence for the current app-wide knowledge set."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.central_knowledge import (
    CentralAssetKind,
    CentralAssetNotFoundError,
    CentralAssetRecord,
)
from app.infrastructure.audit_models import CentralAssetModel
from app.infrastructure.audit_persistence import utcnow


class SqlAlchemyCentralKnowledgeRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def list_assets(self) -> list[CentralAssetRecord]:
        with self._sessions() as session:
            models = session.scalars(
                select(CentralAssetModel).order_by(
                    CentralAssetModel.kind,
                    CentralAssetModel.filename,
                )
            ).all()
            return [_to_record(model) for model in models]

    def get_asset(self, asset_id: str) -> CentralAssetRecord:
        with self._sessions() as session:
            model = session.get(CentralAssetModel, asset_id)
            if model is None:
                raise CentralAssetNotFoundError(asset_id)
            return _to_record(model)

    def find_asset(
        self, kind: CentralAssetKind, filename: str
    ) -> CentralAssetRecord | None:
        with self._sessions() as session:
            model = session.scalar(
                select(CentralAssetModel).where(
                    CentralAssetModel.kind == kind.value,
                    CentralAssetModel.filename == filename,
                )
            )
            return _to_record(model) if model is not None else None

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
    ) -> CentralAssetRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            model = session.scalar(
                select(CentralAssetModel)
                .where(
                    CentralAssetModel.kind == kind.value,
                    CentralAssetModel.filename == filename,
                )
                .with_for_update()
            )
            if model is None:
                model = CentralAssetModel(
                    asset_id=asset_id,
                    kind=kind.value,
                    filename=filename,
                    object_key=object_key,
                    content_hash=content_hash,
                    size_bytes=size_bytes,
                    content_type=content_type,
                    uploaded_by=uploaded_by,
                    created_at=now,
                    updated_at=now,
                )
                session.add(model)
            else:
                model.object_key = object_key
                model.content_hash = content_hash
                model.size_bytes = size_bytes
                model.content_type = content_type
                model.uploaded_by = uploaded_by
                model.updated_at = now
        return _to_record(model)

    def delete_asset(self, asset_id: str) -> CentralAssetRecord:
        with self._sessions.begin() as session:
            model = session.get(CentralAssetModel, asset_id)
            if model is None:
                raise CentralAssetNotFoundError(asset_id)
            record = _to_record(model)
            session.delete(model)
        return record


def _to_record(model: CentralAssetModel) -> CentralAssetRecord:
    return CentralAssetRecord(
        asset_id=model.asset_id,
        kind=CentralAssetKind(model.kind),
        filename=model.filename,
        object_key=model.object_key,
        content_hash=model.content_hash,
        size_bytes=model.size_bytes,
        content_type=model.content_type,
        uploaded_by=model.uploaded_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
