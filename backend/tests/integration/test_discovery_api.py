from io import BytesIO
from pathlib import Path

from app.application.discovery_service import DiscoveryDocument
from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.domain.audit import (
    CandidateIssueInput,
    LogicalRole,
    RiskCategory,
    SourceReferenceInput,
    SourceRefKind,
)
from docx import Document
from fastapi.testclient import TestClient

_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def _settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        repository_root=tmp_path,
        backend_root=tmp_path / "backend",
        data_root=tmp_path / "data",
        cors_origins=(),
        run_workers=1,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
        storage_root=tmp_path / "storage",
    )


def _source_payloads() -> dict[str, bytes]:
    return {
        "audit-project/AWP/scope.docx": _docx_bytes("Audit scope"),
        "audit-project/APM/risk.docx": _docx_bytes("Risk context"),
        "audit-project/Process Understanding/evidence.docx": (
            _docx_bytes("Observed evidence")
        ),
        "audit-project/Process SOP/criteria.docx": (
            _docx_bytes("Expected control")
        ),
        "audit-project/Samples/approved-report.docx": (
            _docx_bytes("Approved prior audit wording")
        ),
    }


def _create_project(client: TestClient) -> tuple[str, str]:
    payloads = _source_payloads()
    session = client.post(
        "/api/v1/upload-sessions",
        json={
            "files": [
                {
                    "relative_path": relative_path,
                    "size_bytes": len(content),
                    "content_type": _CONTENT_TYPE,
                }
                for relative_path, content in payloads.items()
            ]
        },
    )
    assert session.status_code == 201, session.text
    upload_session = session.json()
    for descriptor in upload_session["files"]:
        response = client.put(
            descriptor["upload_url"],
            content=payloads[descriptor["relative_path"]],
            headers={"Content-Type": _CONTENT_TYPE},
        )
        assert response.status_code == 200, response.text
    validated = client.post(
        f"/api/v1/upload-sessions/{upload_session['session_id']}/validate"
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["validation_report"]["valid"] is True
    created = client.post(
        f"/api/v1/upload-sessions/{upload_session['session_id']}/projects",
        json={"name": "Discovery API Test"},
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    return payload["project_id"], payload["version"]["version_id"]


class SuccessfulDiscoveryEngine:
    engine_version = "fake-success-v1"

    def discover(
        self, documents: tuple[DiscoveryDocument, ...]
    ) -> tuple[CandidateIssueInput, ...]:
        assert {document.logical_role for document in documents} == {
            LogicalRole.SCOPE,
            LogicalRole.RISK_CONTEXT,
            LogicalRole.EVIDENCE,
            LogicalRole.CRITERIA,
            LogicalRole.SAMPLE,
        }
        assert all(document.local_path.is_file() for document in documents)
        documents_by_role = {
            document.logical_role: document for document in documents
        }
        return (
            CandidateIssueInput(
                title_hint="Access review evidence is incomplete",
                observed_gap=(
                    "The quarterly access review did not cover all profiles."
                ),
                evidence_summary=(
                    "The review workbook covered three of four profiles."
                ),
                source_refs=(
                    SourceReferenceInput(
                        reference_id="engine-evidence",
                        ref_kind=SourceRefKind.EVIDENCE,
                        document_id=documents_by_role[LogicalRole.EVIDENCE].document_id,
                        location={"description": "Review result"},
                    ),
                    SourceReferenceInput(
                        reference_id="engine-criteria",
                        ref_kind=SourceRefKind.CRITERIA,
                        document_id=documents_by_role[LogicalRole.CRITERIA].document_id,
                        location={"description": "Section 3.2"},
                    ),
                ),
                risk_category=RiskCategory.OPERATIONAL,
            ),
        )


class FlakyDiscoveryEngine(SuccessfulDiscoveryEngine):
    engine_version = "fake-flaky-v1"

    def __init__(self) -> None:
        self.calls = 0

    def discover(
        self, documents: tuple[DiscoveryDocument, ...]
    ) -> tuple[CandidateIssueInput, ...]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("Temporary AI discovery failure")
        return super().discover(documents)


def test_discovery_job_persists_candidate_reference_arrays(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        discovery_engine=SuccessfulDiscoveryEngine(),
    )

    with TestClient(app) as client:
        project_id, version_id = _create_project(client)
        started = client.post(
            f"/api/v1/projects/{project_id}/versions/{version_id}/discovery-jobs",
            json={"force": False},
        )
        assert started.status_code == 202, started.text
        job_id = started.json()["job_id"]

        job = client.get(f"/api/v1/jobs/{job_id}")
        assert job.status_code == 200
        assert job.json()["state"] == "SUCCEEDED"
        assert job.json()["attempt_count"] == 1

        issues = client.get(
            f"/api/v1/projects/{project_id}/versions/{version_id}/issues"
        )
        assert issues.status_code == 200, issues.text
        assert len(issues.json()) == 1
        candidate = issues.json()[0]
        assert candidate["origin"] == "AI_DISCOVERED"
        assert candidate["status"] == "READY_FOR_REVIEW"
        assert candidate["risk_category"] == "Operational"
        source_refs = candidate["source_refs"]
        assert [reference["ref_kind"] for reference in source_refs] == [
            "EVIDENCE",
            "CRITERIA",
        ]
        assert all(
            reference["reference_id"].startswith("engine-") is False
            for reference in source_refs
        )
        assert candidate["evidence_refs"] == [
            f'{source_refs[0]["document_id"]} - Review result'
        ]
        assert candidate["sop_refs"] == [
            f'{source_refs[1]["document_id"]} - Section 3.2'
        ]

        events = client.get(f"/api/v1/jobs/{job_id}/events")
        assert [item["stage"] for item in events.json()] == [
            "PREPARING_SOURCE",
            "SAVING_CANDIDATES",
        ]


def test_issue_risk_category_is_restricted_to_supported_values(
    tmp_path: Path,
) -> None:
    app = create_app(settings=_settings(tmp_path))

    with TestClient(app) as client:
        project_id, version_id = _create_project(client)
        issues_url = (
            f"/api/v1/projects/{project_id}/versions/{version_id}/issues"
        )

        invalid = client.post(
            issues_url,
            json={
                "observed_gap": "A manual issue with an invalid category.",
                "risk_category": "Access Management",
            },
        )
        assert invalid.status_code == 422

        created = client.post(
            issues_url,
            json={
                "observed_gap": "A manual issue with a supported category.",
                "risk_category": "Financial",
            },
        )
        assert created.status_code == 201, created.text
        issue = created.json()
        assert issue["risk_category"] == "Financial"

        invalid_update = client.put(
            f"{issues_url}/{issue['issue_id']}",
            json={
                "row_version": issue["row_version"],
                "observed_gap": issue["observed_gap"],
                "risk_category": "Technology",
            },
        )
        assert invalid_update.status_code == 422

    app.state.database.dispose()


def test_failed_discovery_can_retry_and_succeeded_job_cannot(
    tmp_path: Path,
) -> None:
    engine = FlakyDiscoveryEngine()
    app = create_app(
        settings=_settings(tmp_path),
        discovery_engine=engine,
    )

    with TestClient(app) as client:
        project_id, version_id = _create_project(client)
        started = client.post(
            f"/api/v1/projects/{project_id}/versions/{version_id}/discovery-jobs",
            json={"force": False},
        )
        job_id = started.json()["job_id"]
        failed = client.get(f"/api/v1/jobs/{job_id}").json()
        assert failed["state"] == "FAILED"
        assert failed["error"] == "Temporary AI discovery failure"

        retried = client.post(
            f"/api/v1/jobs/{job_id}/retry",
            json={"reason": "AI dependency recovered"},
        )
        assert retried.status_code == 202, retried.text
        succeeded = client.get(f"/api/v1/jobs/{job_id}").json()
        assert succeeded["state"] == "SUCCEEDED"
        assert succeeded["attempt_count"] == 2
        assert engine.calls == 2

        cannot_retry = client.post(
            f"/api/v1/jobs/{job_id}/retry", json={}
        )
        assert cannot_retry.status_code == 409
        assert (
            cannot_retry.json()["error"]["code"]
            == "JOB_NOT_RETRYABLE"
        )

        events = client.get(f"/api/v1/jobs/{job_id}/events").json()
        assert "FAILED" in [item["stage"] for item in events]
        assert "RETRY_QUEUED" in [item["stage"] for item in events]


def test_default_discovery_engine_fails_as_durable_job(
    tmp_path: Path,
) -> None:
    app = create_app(settings=_settings(tmp_path))

    with TestClient(app) as client:
        project_id, version_id = _create_project(client)
        started = client.post(
            f"/api/v1/projects/{project_id}/versions/{version_id}/discovery-jobs",
            json={"force": False},
        )
        assert started.status_code == 202, started.text

        job = client.get(
            f"/api/v1/jobs/{started.json()['job_id']}"
        ).json()
        assert job["state"] == "FAILED"
        assert "AI discovery engine is not configured" in job["error"]


def test_source_tree_includes_optional_project_samples(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path))
    with TestClient(app) as client:
        project_id, _ = _create_project(client)
        response = client.get(
            f"/api/v1/projects/{project_id}/source-documents"
        )
        assert response.status_code == 200, response.text
        folders = {
            folder["logical_role"]: folder
            for folder in response.json()["folders"]
        }
        assert folders["SAMPLE"]["name"] == "Samples"
        assert folders["SAMPLE"]["file_count"] == 1
        assert folders["SAMPLE"]["files"][0]["name"] == (
            "approved-report.docx"
        )
    app.state.database.dispose()


def test_manual_issue_crud_uses_tagged_source_references(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path))

    with TestClient(app) as client:
        project_id, version_id = _create_project(client)
        tree = client.get(
            f"/api/v1/projects/{project_id}/source-documents"
        )
        assert tree.status_code == 200, tree.text
        documents = {
            file["logical_role"]: file
            for folder in tree.json()["folders"]
            for file in folder["files"]
        }
        issues_url = (
            f"/api/v1/projects/{project_id}/versions/{version_id}/issues"
        )
        create_refs = [
            {
                "ref_kind": "EVIDENCE",
                "document_id": documents["EVIDENCE"]["document_id"],
                "location": {"sheet": "Access Review", "range": "A1:B12"},
                "quote": "Review completed by control owner",
            },
            {
                "ref_kind": "CRITERIA",
                "document_id": documents["CRITERIA"]["document_id"],
                "location": {"description": "Section 3.2"},
            },
        ]
        created_response = client.post(
            issues_url,
            json={
                "observed_gap": "Quarterly access review was incomplete.",
                "source_refs": create_refs,
            },
        )
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()
        assert [item["ref_kind"] for item in created["source_refs"]] == [
            "EVIDENCE",
            "CRITERIA",
        ]
        assert all(item["reference_id"] for item in created["source_refs"])
        assert created["evidence_refs"] == [
            documents["EVIDENCE"]["document_id"]
            + ' - {"range":"A1:B12","sheet":"Access Review"}'
        ]
        assert created["sop_refs"] == [
            documents["CRITERIA"]["document_id"] + " - Section 3.2"
        ]

        fetched = client.get(f'{issues_url}/{created["issue_id"]}')
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["source_refs"] == created["source_refs"]

        update_refs = [
            {
                "ref_kind": "CRITERIA",
                "document_id": documents["SCOPE"]["document_id"],
                "location": {"description": "Control objective 1"},
            }
        ]
        updated_response = client.put(
            f'{issues_url}/{created["issue_id"]}',
            json={
                "row_version": created["row_version"],
                "observed_gap": "Quarterly access review remained incomplete.",
                "source_refs": update_refs,
                "status": "REJECTED",
                "confidence": 0.01,
                "validation_flags": ["client-must-not-own-this"],
            },
        )
        assert updated_response.status_code == 200, updated_response.text
        updated = updated_response.json()
        assert updated["row_version"] == created["row_version"] + 1
        assert updated["status"] == "DRAFT"
        assert updated["confidence"] is None
        assert updated["validation_flags"] == []
        assert [item["ref_kind"] for item in updated["source_refs"]] == [
            "CRITERIA"
        ]
        assert updated["evidence_refs"] == []
        assert updated["sop_refs"] == [
            documents["SCOPE"]["document_id"] + " - Control objective 1"
        ]

        invalid_tag = client.post(
            issues_url,
            json={
                "observed_gap": "Invalid tagged reference.",
                "source_refs": [
                    {
                        **create_refs[0],
                        "ref_kind": "SOP",
                    }
                ],
            },
        )
        assert invalid_tag.status_code == 422

        sample_reference = client.post(
            issues_url,
            json={
                "observed_gap": "Samples cannot prove a new issue.",
                "source_refs": [
                    {
                        "ref_kind": "EVIDENCE",
                        "document_id": documents["SAMPLE"]["document_id"],
                        "location": {},
                    }
                ],
            },
        )
        assert sample_reference.status_code == 422
        assert sample_reference.json()["error"]["code"] == "INVALID_REQUEST"

        unknown_document = client.post(
            issues_url,
            json={
                "observed_gap": "Reference is outside this project.",
                "source_refs": [
                    {
                        "ref_kind": "CRITERIA",
                        "document_id": "unknown-document",
                        "location": {},
                    }
                ],
            },
        )
        assert unknown_document.status_code == 422
        assert unknown_document.json()["error"]["code"] == "INVALID_REQUEST"

    app.state.database.dispose()
