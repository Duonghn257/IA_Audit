from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.bootstrap.api import create_app
from app.core.settings import ApiSettings
from app.domain.audit import (
    JobType,
    LogicalRole,
    UploadFileInput,
    UploadFileValidation,
)
from app.domain.auth import AuthIdentity
from app.infrastructure.audit_models import UploadSessionModel
from app.infrastructure.audit_repository import SqlAlchemyAuditRepository
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
        google_redirect_uri=("http://testserver/api/v1/auth/google/callback"),
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
            "/api/v1/auth/google/callback?code=valid-code&state=test-state",
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
        hidden_session = client.get(f"/api/v1/upload-sessions/{upload_session_id}")
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


def _promote_project_for_user(
    app,
    *,
    owner_user_id: str,
    suffix: str,
) -> tuple[str, str, str]:
    repository = SqlAlchemyAuditRepository(app.state.database.sessions)
    session_id = f"upload-{suffix}"
    file_id = f"file-{suffix}"
    repository.create_upload_session(
        session_id=session_id,
        files=[
            UploadFileInput(
                file_id=file_id,
                relative_path="Process Understanding/evidence.docx",
                size_bytes=10,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                staging_object_key=f"staging/{session_id}/{file_id}",
            )
        ],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        actor_id=owner_user_id,
        actor_label=f"User {suffix}",
        actor_type="GOOGLE",
    )
    repository.complete_upload_validation(
        session_id,
        validation_report={"errors": [], "warnings": []},
        files=[
            UploadFileValidation(
                file_id=file_id,
                content_hash=f"sha256:{suffix}",
                logical_role=LogicalRole.EVIDENCE,
                readability_status="READABLE",
            )
        ],
        valid=True,
    )
    project, version = repository.promote_upload_session(
        session_id,
        project_id=f"project-{suffix}",
        source_snapshot_id=f"snapshot-{suffix}",
        version_id=f"version-{suffix}",
        owner_user_id=owner_user_id,
        name="Same project name",
        manifest_hash=f"sha256:manifest-{suffix}",
        source_object_prefix=f"projects/project-{suffix}/source",
    )
    job = repository.enqueue_job(
        project.project_id,
        version.version_id,
        job_id=f"job-{suffix}",
        job_type=JobType.DISCOVERY,
        input_hash=f"sha256:input-{suffix}",
        correlation_id=f"correlation-{suffix}",
    )
    return project.project_id, version.version_id, job.job_id


def test_projects_versions_and_jobs_are_isolated_by_authenticated_user(
    tmp_path: Path,
) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        google_oauth_client=FakeGoogleOAuthClient(),
    )
    first_session, first_token = app.state.auth_service.sign_in(
        AuthIdentity(
            provider="GOOGLE",
            provider_subject="isolation-user-1",
            email="isolation-1@example.com",
            email_verified=True,
            display_name="Isolation User 1",
        )
    )
    second_session, second_token = app.state.auth_service.sign_in(
        AuthIdentity(
            provider="GOOGLE",
            provider_subject="isolation-user-2",
            email="isolation-2@example.com",
            email_verified=True,
            display_name="Isolation User 2",
        )
    )
    first_project, first_version, first_job = _promote_project_for_user(
        app, owner_user_id=first_session.user.user_id, suffix="one"
    )
    second_project, second_version, second_job = _promote_project_for_user(
        app, owner_user_id=second_session.user.user_id, suffix="two"
    )

    with TestClient(app) as client:
        client.cookies.set("audit_session", first_token)
        listed = client.get("/api/v1/projects")
        assert listed.status_code == 200
        assert [item["project_id"] for item in listed.json()] == [first_project]
        assert client.get(f"/api/v1/projects/{first_project}").status_code == 200
        assert client.get(f"/api/v1/projects/{second_project}").status_code == 404
        assert (
            client.get(f"/api/v1/projects/{second_project}/versions").status_code == 404
        )
        assert client.get(f"/api/v1/jobs/{second_job}").status_code == 404
        cross_retry = client.post(
            f"/api/v1/jobs/{second_job}/retry",
            json={},
            headers={"X-CSRF-Token": first_session.csrf_token},
        )
        assert cross_retry.status_code == 404

        assert (
            client.get(
                f"/api/v1/projects/{first_project}/versions/{first_version}"
            ).status_code
            == 200
        )
        created_version = client.post(
            f"/api/v1/projects/{first_project}/versions",
            json={"base_version_id": first_version},
            headers={"X-CSRF-Token": first_session.csrf_token},
        )
        assert created_version.status_code == 201, created_version.text
        created_payload = created_version.json()
        assert created_payload["label"] == "v0.2"
        assert created_payload["base_version_id"] == first_version
        assert created_payload["created_by_user_id"] == first_session.user.user_id
        assert created_payload["created_by_name"] == "Isolation User 1"
        assert created_payload["state"] == "DRAFT"
        assert created_payload["issue_revision"] == 0
        assert created_payload["issue_counts"] == {}
        assert created_payload["output_available"] is False
        assert created_payload["output_status"] is None
        assert client.get(f"/api/v1/jobs/{first_job}").status_code == 200

        client.cookies.set("audit_session", second_token)
        listed = client.get("/api/v1/projects")
        assert listed.status_code == 200
        assert [item["project_id"] for item in listed.json()] == [second_project]
        assert (
            client.get(
                f"/api/v1/projects/{first_project}/versions/{first_version}"
            ).status_code
            == 404
        )
        assert client.get(f"/api/v1/jobs/{first_job}").status_code == 404
        assert (
            client.get(
                f"/api/v1/projects/{second_project}/versions/{second_version}"
            ).status_code
            == 200
        )

    app.state.database.dispose()


def test_google_callback_rejects_state_mismatch(tmp_path: Path) -> None:
    app = create_app(
        settings=_settings(tmp_path),
        google_oauth_client=FakeGoogleOAuthClient(),
    )
    with TestClient(app) as client:
        client.get("/api/v1/auth/google/login", follow_redirects=False)
        response = client.get(
            "/api/v1/auth/google/callback?code=valid-code&state=wrong-state",
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
            "google_redirect_uri": ("http://testserver/api/auth/callback/google"),
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
            "/api/auth/callback/google?code=valid-code&state=test-state",
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
