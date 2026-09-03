from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.settings import load_api_settings
from app.domain.audit import IssueOrigin, IssueStatus, SourceRefKind
from app.infrastructure.audit_repository import SqlAlchemyAuditRepository
from app.infrastructure.database import Database
from sqlalchemy import create_engine, inspect, text
from tests.unit.test_audit_repository import _create_project

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
        "central_assets",
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
    version_columns = {
        column["name"] for column in schema.get_columns("project_versions")
    }
    assert {"created_by_user_id", "created_by_name"} <= version_columns
    assert "ix_project_versions_created_by_user_id" in {
        index["name"] for index in schema.get_indexes("project_versions")
    }
    engine.dispose()

    command.check(config)


def test_unified_source_reference_migration_backfills_unambiguous_legacy_refs(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "legacy-references.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "20260903_06")

    database = Database(database_url)
    repository = SqlAlchemyAuditRepository(database.sessions)
    _, version_id = _create_project(repository)
    repository.create_issue(
        version_id,
        issue_id="legacy-issue",
        origin=IssueOrigin.AI_DISCOVERED,
        status=IssueStatus.READY_FOR_REVIEW,
        title_hint="Legacy issue",
        observed_gap="Legacy gap",
        evidence_summary="Legacy evidence summary",
    )
    with database.engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE issues
                SET evidence_refs = :evidence_refs,
                    sop_refs = :sop_refs
                WHERE issue_id = :issue_id
                """
            ),
            {
                "evidence_refs": '["Evidence/access-review.xlsx - Sheet A"]',
                "sop_refs": '["access-review.xlsx - Section 3.2"]',
                "issue_id": "legacy-issue",
            },
        )
    database.dispose()

    command.upgrade(config, "head")

    migrated_database = Database(database_url)
    migrated = SqlAlchemyAuditRepository(
        migrated_database.sessions
    ).get_issue(version_id, "legacy-issue")
    assert [reference.ref_kind for reference in migrated.source_refs] == [
        SourceRefKind.EVIDENCE,
        SourceRefKind.CRITERIA,
    ]
    assert [reference.location for reference in migrated.source_refs] == [
        {"description": "Sheet A"},
        {"description": "Section 3.2"},
    ]
    migrated_database.dispose()
