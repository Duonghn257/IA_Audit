from datetime import datetime, timedelta, timezone

from app.domain.projects import ProjectStatus
from app.infrastructure.database import Database
from app.infrastructure.project_repository import (
    SqlAlchemyProjectRepository,
)


def test_project_repository_persists_state_and_progress(tmp_path) -> None:
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'projects.db'}")
    database.create_schema()
    repository = SqlAlchemyProjectRepository(database.sessions)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    created = repository.create(
        project_id="project-1",
        owner_user_id="user-1",
        name="FY2024 Audit",
        raw_expires_at=expires_at,
    )
    repository.set_upload_saved(
        created.project_id,
        storage_path="/storage/project-1/input",
    )
    repository.mark_processing(created.project_id)
    event = repository.append_progress(
        created.project_id,
        stage="PARSING",
        message="Reading APM...",
        completed_steps=1,
        total_steps=8,
        warning=False,
    )
    completed = repository.mark_completed(
        created.project_id,
        output_path="/storage/project-1/output/report.docx",
        version="v0.1",
        issue_count=2,
    )

    assert completed.status == ProjectStatus.COMPLETED
    assert completed.current_activity == "DOCX ready to download"
    assert repository.get(created.project_id, owner_user_id="user-1").issue_count == 2
    assert repository.list_events(created.project_id, owner_user_id="user-1") == [event]
    assert repository.list(owner_user_id="user-1")[0].project_id == created.project_id

    database.dispose()
