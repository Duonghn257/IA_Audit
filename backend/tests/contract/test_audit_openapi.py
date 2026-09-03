from pathlib import Path

from app.bootstrap.api import create_app
from app.core.settings import ApiSettings


def test_openapi_publishes_v2_workspace_contract(tmp_path: Path) -> None:
    settings = ApiSettings(
        repository_root=tmp_path,
        backend_root=tmp_path / "backend",
        data_root=tmp_path / "data",
        cors_origins=(),
        run_workers=1,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
        storage_root=tmp_path / "storage",
    )
    app = create_app(settings=settings)
    assert app.openapi()["components"]["schemas"]["RiskCategory"]["enum"] == [
        "Compliance",
        "Operational",
        "Strategic",
        "Financial",
    ]
    paths = app.openapi()["paths"]

    assert set(paths["/api/v1/projects/{project_id}/versions"]) == {"get", "post"}
    assert set(paths["/api/v1/projects/{project_id}/versions/{version_id}/issues"]) == {
        "get",
        "post",
    }
    audit_operation = paths[
        "/api/v1/projects/{project_id}/versions/{version_id}/audit-jobs"
    ]["post"]
    assert "501" not in audit_operation["responses"]
    assert "get" in paths["/api/v1/jobs/{job_id}/events/stream"]
    assert "get" in paths["/api/v1/auth/google/login"]
    assert "get" in paths["/api/v1/auth/google/callback"]
    assert "get" in paths["/api/v1/auth/me"]
    assert "post" in paths["/api/v1/auth/logout"]
    assert "post" in paths["/api/v1/upload-sessions"]
    assert "put" in paths[
        "/api/v1/upload-sessions/{session_id}/files/{file_id}"
    ]
    assert "get" in paths["/api/v1/outputs/{output_id}/download"]
    assert "get" in paths["/api/v1/central-knowledge"]
    assert "post" in paths["/api/v1/central-knowledge/guidelines"]
    assert "put" in paths["/api/v1/central-knowledge/template"]
    assert "delete" in paths["/api/v1/central-knowledge/files/{asset_id}"]
    assert not any(path.startswith("/api/v1/runs") for path in paths)

    app.state.run_manager.shutdown()
    app.state.project_manager.shutdown()
    app.state.database.dispose()
