from io import BytesIO
from pathlib import Path

from app.application.discovery_service import DiscoveryDocument
from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.domain.audit import CandidateIssueInput, LogicalRole, RiskCategory
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
        }
        assert all(document.local_path.is_file() for document in documents)
        return (
            CandidateIssueInput(
                title_hint="Access review evidence is incomplete",
                observed_gap=(
                    "The quarterly access review did not cover all profiles."
                ),
                evidence_summary=(
                    "The review workbook covered three of four profiles."
                ),
                evidence_refs=(
                    "Process Understanding/evidence.docx - Review result",
                ),
                sop_refs=("Process SOP/criteria.docx - Section 3.2",),
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
        assert candidate["evidence_refs"] == [
            "Process Understanding/evidence.docx - Review result"
        ]
        assert candidate["sop_refs"] == [
            "Process SOP/criteria.docx - Section 3.2"
        ]
        assert candidate["source_refs"] == []

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
