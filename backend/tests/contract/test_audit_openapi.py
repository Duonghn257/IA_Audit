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

    paths = app.openapi()["paths"]

    assert set(paths["/api/v1/projects/{project_id}/versions"]) == {"get", "post"}
    assert set(paths["/api/v1/projects/{project_id}/versions/{version_id}/issues"]) == {
        "get",
        "post",
    }
    assert "post" in paths["/api/v1/projects/{project_id}/versions/{version_id}/audit-jobs"]
    assert "get" in paths["/api/v1/jobs/{job_id}/events/stream"]
    assert "post" in paths["/api/v1/upload-sessions"]
    assert "get" in paths["/api/v1/outputs/{output_id}/download"]
    assert not any(path.startswith("/api/v1/runs") for path in paths)

    app.state.run_manager.shutdown()
    app.state.project_manager.shutdown()
    app.state.database.dispose()
