"""Schemas for immutable project source trees."""
from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel

from app.application.audit_workspace_service import SourceTree
from app.domain.audit import LogicalRole


class SourceFileResponse(BaseModel):
    document_id: str
    name: str
    relative_path: str
    logical_role: LogicalRole
    size_bytes: int
    content_type: str | None
    status: str
    parse_status: str


class SourceFolderResponse(BaseModel):
    name: str
    logical_role: LogicalRole
    file_count: int
    files: list[SourceFileResponse]


class SourceTreeResponse(BaseModel):
    snapshot_id: str
    status: str
    folder_count: int
    file_count: int
    total_size_bytes: int
    folders: list[SourceFolderResponse]

    @classmethod
    def from_domain(cls, tree: SourceTree) -> "SourceTreeResponse":
        folders = [
            SourceFolderResponse(
                name=folder.name,
                logical_role=LogicalRole(folder.logical_role),
                file_count=len(folder.files),
                files=[
                    SourceFileResponse(
                        document_id=document.document_id,
                        name=PurePosixPath(document.relative_path).name,
                        relative_path=document.relative_path,
                        logical_role=document.logical_role,
                        size_bytes=document.size_bytes,
                        content_type=document.content_type,
                        status="READY",
                        parse_status=document.parse_status,
                    )
                    for document in folder.files
                ],
            )
            for folder in tree.folders
        ]
        return cls(
            snapshot_id=tree.snapshot_id,
            status="FROZEN",
            folder_count=len(folders),
            file_count=sum(folder.file_count for folder in folders),
            total_size_bytes=sum(
                file.size_bytes for folder in folders for file in folder.files
            ),
            folders=folders,
        )
