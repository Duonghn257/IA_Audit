from pathlib import Path

from fastapi.testclient import TestClient

from app.application.audit_pipeline import PipelineRequest
from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.infrastructure.run_store import InMemoryRunStore


class FakeRunManager:
    def __init__(self) -> None:
        self.store = InMemoryRunStore()

    def submit(self, request: PipelineRequest):
        return self.store.create(
            str(request.project_path),
            str(request.issues_path),
        )

    def get(self, run_id: str):
        return self.store.get(run_id)

    def list(self):
        return self.store.list()

    def list_events(self, run_id: str, *, after_event_id: int = 0):
        return self.store.list_events(
            run_id,
            after_event_id=after_event_id,
        )

    def shutdown(self) -> None:
        return None


def _settings(
    repository_root: Path,
    *,
    data_root: Path | None = None,
) -> ApiSettings:
    return ApiSettings(
        repository_root=repository_root,
        backend_root=repository_root / "backend",
        data_root=data_root or repository_root / "data",
        cors_origins=("http://localhost:5173",),
        run_workers=1,
    )


def test_health_endpoint() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    app = create_app(
        settings=_settings(repository_root),
        run_manager=FakeRunManager(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Correlation-ID"]


def test_create_and_get_run(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    project_path = data_root / "project"
    project_path.mkdir(parents=True)
    issues_path = tmp_path / "issues.json"
    issues_path.write_text("[]", encoding="utf-8")
    app = create_app(
        settings=_settings(tmp_path, data_root=data_root),
        run_manager=FakeRunManager(),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/runs",
            json={
                "project_path": str(project_path),
                "issues_path": str(issues_path),
            },
        )
        fetched = client.get(
            f"/api/v1/runs/{created.json()['run_id']}"
        )

    assert created.status_code == 202
    assert created.json()["status"] == "QUEUED"
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == created.json()["run_id"]


def test_create_run_rejects_path_outside_data_root() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    app = create_app(
        settings=_settings(repository_root),
        run_manager=FakeRunManager(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            json={
                "project_path": "backend",
                "issues_path": "backend/sample_issues.json",
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_RUN_PATH"


def test_unknown_run_uses_stable_error_contract() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    app = create_app(
        settings=_settings(repository_root),
        run_manager=FakeRunManager(),
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
