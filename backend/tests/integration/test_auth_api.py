from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.domain.auth import AuthIdentity
from app.infrastructure.audit_models import UploadSessionModel
from app.infrastructure.auth_repository import AuthSessionModel


class FakeGoogleOAuthClient:
    def create_transaction(self) -> tuple[str, str, str, str]:
        return "test-state", "test-verifier", "test-nonce", "test-challenge"

    def authorization_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
    ) -> str:
        return "https://accounts.google.test/auth?" + urlencode(
            {
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
            }
        )

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        expected_nonce: str,
    ) -> AuthIdentity:
        assert code == "valid-code"
        assert code_verifier == "test-verifier"
        assert expected_nonce == "test-nonce"
        return AuthIdentity(
            provider="GOOGLE",
            provider_subject="google-user-1",
            email="auditor@example.com",
            email_verified=True,
            display_name="UAT Auditor",
            picture_url="https://example.com/avatar.png",
            hosted_domain="example.com",
        )


def _settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        repository_root=tmp_path,
        backend_root=tmp_path / "backend",
        data_root=tmp_path / "data",
        cors_origins=(),
        run_workers=1,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'auth.db'}",
        storage_root=tmp_path / "storage",
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_redirect_uri=(
            "http://testserver/api/v1/auth/google/callback"
        ),
        auth_cookie_secure=False,
    )


def test_google_login_creates_server_session_and_protects_uploads(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        google_oauth_client=FakeGoogleOAuthClient(),
    )

    with TestClient(app) as client:
        anonymous = client.get("/api/v1/auth/me")
        protected = client.get("/api/v1/projects")
        assert anonymous.status_code == 401
        assert protected.status_code == 401

        login = client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )
        assert login.status_code == 302
        assert login.headers["location"].startswith(
            "https://accounts.google.test/auth?"
        )

        callback = client.get(
            "/api/v1/auth/google/callback"
            "?code=valid-code&state=test-state",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "/tests-ui/"

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        auth = me.json()
        assert auth["auth_enabled"] is True
        assert auth["user"]["email"] == "auditor@example.com"
        assert auth["csrf_token"]

        manifest = {
            "files": [
                {
                    "relative_path": "AWP/scope.docx",
                    "size_bytes": 10,
                    "content_type": (
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document"
                    ),
                }
            ]
        }
        rejected = client.post(
            "/api/v1/upload-sessions",
            json=manifest,
        )
        assert rejected.status_code == 403
        assert rejected.json()["error"]["code"] == "CSRF_TOKEN_INVALID"

        created = client.post(
            "/api/v1/upload-sessions",
            json=manifest,
            headers={"X-CSRF-Token": auth["csrf_token"]},
        )
        assert created.status_code == 201, created.text
        upload_session_id = created.json()["session_id"]

        raw_cookie = client.cookies.get("audit_session")
        assert raw_cookie
        with app.state.database.sessions() as session:
            stored_session = session.scalar(select(AuthSessionModel))
            stored_upload = session.get(
                UploadSessionModel,
                upload_session_id,
            )
            assert stored_session is not None
            assert stored_session.token_hash != raw_cookie
            assert stored_upload is not None
            first_user_id = stored_upload.actor_id

        second_session, second_token = app.state.auth_service.sign_in(
            AuthIdentity(
                provider="GOOGLE",
                provider_subject="google-user-2",
                email="other@example.com",
                email_verified=True,
                display_name="Other Auditor",
            )
        )
        client.cookies.set("audit_session", second_token)
        other_me = client.get("/api/v1/auth/me")
        assert other_me.status_code == 200
        assert second_session.user.user_id != first_user_id
        hidden_session = client.get(
            f"/api/v1/upload-sessions/{upload_session_id}"
        )
        assert hidden_session.status_code == 404

        logout = client.post(
            "/api/v1/auth/logout",
            headers={
                "X-CSRF-Token": other_me.json()["csrf_token"],
            },
        )
        assert logout.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

    app.state.database.dispose()


def test_google_callback_rejects_state_mismatch(tmp_path: Path) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        google_oauth_client=FakeGoogleOAuthClient(),
    )
    with TestClient(app) as client:
        client.get("/api/v1/auth/google/login", follow_redirects=False)
        response = client.get(
            "/api/v1/auth/google/callback"
            "?code=valid-code&state=wrong-state",
            follow_redirects=False,
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_OAUTH_CALLBACK"
    app.state.database.dispose()


def test_configured_google_callback_alias_completes_login(
    tmp_path: Path,
) -> None:
    base_settings = _settings(tmp_path)
    settings = ApiSettings(
        **{
            **base_settings.__dict__,
            "google_redirect_uri": (
                "http://testserver/api/auth/callback/google"
            ),
        }
    )
    app = create_app(
        settings=settings,
        google_oauth_client=FakeGoogleOAuthClient(),
    )
    with TestClient(app) as client:
        login = client.get(
            "/api/v1/auth/google/login",
            follow_redirects=False,
        )
        assert login.status_code == 302
        callback = client.get(
            "/api/auth/callback/google"
            "?code=valid-code&state=test-state",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "/tests-ui/"
        assert client.get("/api/v1/auth/me").status_code == 200
    app.state.database.dispose()


def test_backend_serves_standalone_test_ui(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    settings = ApiSettings(
        repository_root=repository_root,
        backend_root=repository_root / "backend",
        data_root=tmp_path / "data",
        cors_origins=(),
        run_workers=1,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'static.db'}",
        storage_root=tmp_path / "storage",
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        response = client.get("/tests-ui/")
    assert response.status_code == 200
    assert "Audit Report API Test UI" in response.text
    app.state.database.dispose()
