from pathlib import Path

from fastapi.testclient import TestClient

from app.bootstrap.api import create_app
from app.core.settings import ApiSettings


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
    app = create_app(settings=_settings(repository_root))

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Correlation-ID"]
