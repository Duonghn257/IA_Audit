from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.settings import load_api_settings
from sqlalchemy import create_engine, inspect

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_environment_database_url_overrides_dotenv(monkeypatch) -> None:
    expected = "sqlite+pysqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", expected)

    assert load_api_settings().database_url == expected


def test_migrations_create_uat_workspace_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    schema = inspect(engine)
    assert set(schema.get_table_names()) == {
        "alembic_version",
        "audit_input_snapshots",
        "auth_sessions",
        "auth_users",
        "issue_source_refs",
        "issues",
        "job_events",
        "jobs",
        "output_revisions",
        "project_events",
        "project_versions",
        "projects",
        "source_documents",
        "source_snapshots",
        "upload_files",
        "upload_sessions",
    }
    assert {column["name"] for column in schema.get_columns("projects")} >= {
        "owner_user_id"
    }
    assert {index["name"] for index in schema.get_indexes("projects")} == {
        "ix_projects_owner_user_id",
        "ix_projects_raw_expires_at",
        "ix_projects_status",
        "uq_projects_owner_name",
    }
    assert schema.get_foreign_keys("auth_sessions")[0]["referred_table"] == "auth_users"
    assert schema.get_foreign_keys("project_events")[0]["referred_table"] == "projects"
    assert (
        schema.get_foreign_keys("source_snapshots")[0]["referred_table"] == "projects"
    )
    assert schema.get_foreign_keys("issues")[0]["referred_table"] == "project_versions"
    issue_columns = {column["name"] for column in schema.get_columns("issues")}
    assert {"evidence_refs", "sop_refs"} <= issue_columns
    engine.dispose()

    command.check(config)
