import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.application.audit_pipeline import (
    PipelineProgress,
    PipelineResult,
)
from app.application.project_manager import ProjectManager
from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.infrastructure.database import Database
from app.infrastructure.project_repository import (
    SqlAlchemyProjectRepository,
)
from app.infrastructure.project_storage import LocalProjectStorage
from app.infrastructure.run_store import InMemoryRunStore


class FakeRunManager:
    def __init__(self) -> None:
        self.store = InMemoryRunStore()

    def shutdown(self) -> None:
        return None


class FakePipeline:
    def run(self, request, *, reporter=None) -> PipelineResult:
        if reporter:
            reporter(
                PipelineProgress(
                    stage="PARSING",
                    message="Reading APM...",
                    completed_steps=1,
                )
            )
        run_directory = request.project_path / "Output" / "v0.1"
        run_directory.mkdir(parents=True)
        output_path = run_directory / "Audit Issue Log v0.1.docx"
        output_path.write_bytes(b"fake-docx")
        return PipelineResult(
            version="v0.1",
            run_directory=run_directory,
            output_path=output_path,
            issue_count=2,
        )


def _build_app(tmp_path: Path):
    database = Database(
        f"sqlite+pysqlite:///{tmp_path / 'projects.db'}"
    )
    database.create_schema()
    repository = SqlAlchemyProjectRepository(database.sessions)
    storage = LocalProjectStorage(
        tmp_path / "storage",
        max_files=20,
        max_total_bytes=1024 * 1024,
    )
    project_manager = ProjectManager(
        repository=repository,
        storage=storage,
        raw_retention_days=7,
        max_workers=1,
        pipeline_factory=FakePipeline,
    )
    settings = ApiSettings(
        repository_root=tmp_path,
        backend_root=tmp_path / "backend",
        data_root=tmp_path / "data",
        cors_origins=("http://localhost:5173",),
        run_workers=1,
    )
    return (
        create_app(
            settings=settings,
            run_manager=FakeRunManager(),
            project_manager=project_manager,
        ),
        database,
    )


def test_folder_upload_completes_and_downloads_docx(tmp_path) -> None:
    app, database = _build_app(tmp_path)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/upload",
            data={
                "name": "CDL Hospitality Trusts Audit FY2024",
                "relative_paths": [
                    "CDL Audit/sample_issues.json",
                    "CDL Audit/APM/apm.txt",
                ],
            },
            files=[
                (
                    "files",
                    ("sample_issues.json", b"[]", "application/json"),
                ),
                ("files", ("apm.txt", b"APM", "text/plain")),
            ],
        )

        assert response.status_code == 202, response.text
        project_id = response.json()["project_id"]
        project = _wait_for_terminal(client, project_id)
        events = client.get(
            f"/api/v1/projects/{project_id}/events"
        )
        output = client.get(
            f"/api/v1/projects/{project_id}/output"
        )

    assert project["status"] == "COMPLETED"
    assert project["output_available"] is True
    assert project["allowed_actions"] == [
        "VIEW_STATUS",
        "VIEW_PROGRESS",
        "DOWNLOAD_OUTPUT",
    ]
    assert [event["stage"] for event in events.json()] == [
        "UPLOAD",
        "PARSING",
    ]
    assert output.status_code == 200
    assert output.content == b"fake-docx"
    database.dispose()


def test_missing_auditor_input_marks_project_failed(tmp_path) -> None:
    app, database = _build_app(tmp_path)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects/upload",
            data={
                "name": "Invalid Project",
                "relative_paths": ["Invalid Project/APM/apm.txt"],
            },
            files=[
                ("files", ("apm.txt", b"APM", "text/plain")),
            ],
        )
        project = _wait_for_terminal(
            client,
            response.json()["project_id"],
        )

    assert project["status"] == "FAILED"
    assert "Missing sample_issues.json" in project["error"]
    assert project["output_available"] is False
    database.dispose()


def _wait_for_terminal(
    client: TestClient,
    project_id: str,
) -> dict:
    for _ in range(100):
        response = client.get(f"/api/v1/projects/{project_id}")
        payload = response.json()
        if payload["status"] in {"COMPLETED", "FAILED"}:
            return payload
        time.sleep(0.01)
    raise AssertionError("Project did not reach a terminal status")
