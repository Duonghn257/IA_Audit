from datetime import datetime, timezone

import pytest

from app.application.audit_execution_service import _serialise_issue, _validate_issue
from app.domain.audit import (
    AuditPreflightError,
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    RiskCategory,
    SourceReferenceRecord,
    SourceRefKind,
)


def _candidate(
    source_refs: tuple[SourceReferenceRecord, ...],
    *,
    evidence_refs: tuple[str, ...] = (),
    sop_refs: tuple[str, ...] = (),
) -> IssueRecord:
    now = datetime.now(timezone.utc)
    return IssueRecord(
        issue_id="issue-1",
        project_version_id="version-1",
        origin=IssueOrigin.AI_DISCOVERED,
        status=IssueStatus.READY_FOR_REVIEW,
        observed_gap="The review did not cover all profiles.",
        title_hint="Incomplete profile review",
        evidence_summary="Three of four profiles were reviewed.",
        risk_category=RiskCategory.OPERATIONAL,
        confidence=0.9,
        validation_flags=[],
        row_version=1,
        created_at=now,
        updated_at=now,
        evidence_refs=evidence_refs,
        sop_refs=sop_refs,
        source_refs=source_refs,
    )


def _reference(kind: SourceRefKind, document_id: str) -> SourceReferenceRecord:
    return SourceReferenceRecord(
        reference_id=f"ref-{kind.value.lower()}",
        ref_kind=kind,
        document_id=document_id,
        location={"description": f"{kind.value.title()} location"},
    )


def test_ai_candidate_preflight_requires_both_source_reference_tags() -> None:
    evidence = _reference(SourceRefKind.EVIDENCE, "evidence-doc")
    with pytest.raises(AuditPreflightError, match=r"source_refs\[CRITERIA\]"):
        _validate_issue(_candidate((evidence,)))

    criteria = _reference(SourceRefKind.CRITERIA, "criteria-doc")
    _validate_issue(_candidate((evidence, criteria)))


def test_audit_payload_derives_legacy_arrays_from_source_references() -> None:
    evidence = _reference(SourceRefKind.EVIDENCE, "evidence-doc")
    criteria = _reference(SourceRefKind.CRITERIA, "criteria-doc")

    payload = _serialise_issue(
        _candidate(
            (evidence, criteria),
            evidence_refs=("stale evidence",),
            sop_refs=("stale criteria",),
        )
    )

    assert payload["evidence_refs"] == ["evidence-doc - Evidence location"]
    assert payload["sop_refs"] == ["criteria-doc - Criteria location"]
    assert [item["ref_kind"] for item in payload["source_refs"]] == [
        "EVIDENCE",
        "CRITERIA",
    ]


def test_legacy_ai_candidate_remains_auditable_during_migration() -> None:
    _validate_issue(
        _candidate(
            (),
            evidence_refs=("legacy evidence",),
            sop_refs=("legacy criteria",),
        )
    )
