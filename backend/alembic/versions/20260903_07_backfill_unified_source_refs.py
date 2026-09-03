"""backfill canonical issue source references

Revision ID: 20260903_07
Revises: 20260903_06
Create Date: 2026-09-03
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_07"
down_revision: str | None = "20260903_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

issues = sa.table(
    "issues",
    sa.column("issue_id", sa.String),
    sa.column("project_version_id", sa.String),
    sa.column("evidence_refs", sa.JSON),
    sa.column("sop_refs", sa.JSON),
)
project_versions = sa.table(
    "project_versions",
    sa.column("version_id", sa.String),
    sa.column("project_id", sa.String),
)
source_snapshots = sa.table(
    "source_snapshots",
    sa.column("snapshot_id", sa.String),
    sa.column("project_id", sa.String),
)
source_documents = sa.table(
    "source_documents",
    sa.column("document_id", sa.String),
    sa.column("snapshot_id", sa.String),
    sa.column("relative_path", sa.String),
    sa.column("logical_role", sa.String),
)
issue_source_refs = sa.table(
    "issue_source_refs",
    sa.column("reference_id", sa.String),
    sa.column("issue_id", sa.String),
    sa.column("ref_kind", sa.String),
    sa.column("document_id", sa.String),
    sa.column("unit_id", sa.String),
    sa.column("location", sa.JSON),
    sa.column("quote", sa.Text),
)


def upgrade() -> None:
    bind = op.get_bind()
    existing_issue_ids = set(
        bind.execute(sa.select(issue_source_refs.c.issue_id)).scalars()
    )
    rows = bind.execute(
        sa.select(
            issues.c.issue_id,
            issues.c.evidence_refs,
            issues.c.sop_refs,
            source_documents.c.document_id,
            source_documents.c.relative_path,
            source_documents.c.logical_role,
        )
        .select_from(
            issues.join(
                project_versions,
                issues.c.project_version_id == project_versions.c.version_id,
            )
            .join(
                source_snapshots,
                project_versions.c.project_id == source_snapshots.c.project_id,
            )
            .join(
                source_documents,
                source_snapshots.c.snapshot_id == source_documents.c.snapshot_id,
            )
        )
        .order_by(issues.c.issue_id, source_documents.c.relative_path)
    ).mappings()

    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        entry = grouped.setdefault(
            row["issue_id"],
            {
                "evidence_refs": row["evidence_refs"] or [],
                "sop_refs": row["sop_refs"] or [],
                "documents": [],
            },
        )
        entry["documents"].append(
            (
                row["document_id"],
                row["relative_path"],
                row["logical_role"],
            )
        )

    inserts: list[dict[str, object]] = []
    for issue_id, entry in grouped.items():
        if issue_id in existing_issue_ids:
            continue
        legacy_refs = [
            ("EVIDENCE", value)
            for value in entry["evidence_refs"]
            if isinstance(value, str) and value.strip()
        ] + [
            ("CRITERIA", value)
            for value in entry["sop_refs"]
            if isinstance(value, str) and value.strip()
        ]
        if not legacy_refs:
            continue
        converted = [
            _convert_reference(issue_id, kind, value, entry["documents"])
            for kind, value in legacy_refs
        ]
        if any(value is None for value in converted):
            continue
        inserts.extend(value for value in converted if value is not None)

    if inserts:
        bind.execute(sa.insert(issue_source_refs), inserts)


def downgrade() -> None:
    # The legacy JSON arrays are retained, so no destructive reverse data
    # migration is necessary.
    pass


def _convert_reference(
    issue_id: str,
    kind: str,
    value: str,
    documents: list[tuple[str, str, str]],
) -> dict[str, object] | None:
    text = value.strip()
    matches: list[tuple[str, str, str]] = []
    for document in documents:
        _, relative_path, logical_role = document
        if logical_role == "SAMPLE":
            continue
        names = (relative_path, PurePosixPath(relative_path).name)
        if any(text == name or text.startswith(f"{name} - ") for name in names):
            matches.append(document)
    if len(matches) != 1:
        return None
    document_id, relative_path, _ = matches[0]
    basename = PurePosixPath(relative_path).name
    prefix = next(
        name
        for name in (relative_path, basename)
        if text == name or text.startswith(f"{name} - ")
    )
    description = text[len(prefix) :].removeprefix(" - ").strip()
    return {
        "reference_id": str(uuid4()),
        "issue_id": issue_id,
        "ref_kind": kind,
        "document_id": document_id,
        "unit_id": None,
        "location": {"description": description} if description else {},
        "quote": None,
    }
