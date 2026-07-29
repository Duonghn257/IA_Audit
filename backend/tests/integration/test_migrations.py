from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.settings import load_api_settings


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_environment_database_url_overrides_dotenv(monkeypatch) -> None:
    expected = "sqlite+pysqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", expected)

    assert load_api_settings().database_url == expected


def test_initial_migration_matches_project_schema(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    schema = inspect(engine)
    assert set(schema.get_table_names()) == {
        "alembic_version",
        "project_events",
        "projects",
    }
    assert {
        index["name"] for index in schema.get_indexes("projects")
    } == {
        "ix_projects_raw_expires_at",
        "ix_projects_status",
    }
    assert schema.get_foreign_keys("project_events")[0][
        "referred_table"
    ] == "projects"
    engine.dispose()

    command.check(config)
