from pathlib import Path

import pytest

from app.application.audit_pipeline import (
    AuditPipeline,
    PipelineInputError,
    PipelineRequest,
)


def test_pipeline_rejects_missing_project_before_loading_config(
    tmp_path: Path,
) -> None:
    issues_path = tmp_path / "issues.json"
    issues_path.write_text("[]", encoding="utf-8")

    with pytest.raises(PipelineInputError, match="is not a directory"):
        AuditPipeline().run(
            PipelineRequest(
                project_path=tmp_path / "missing-project",
                issues_path=issues_path,
            )
        )


def test_pipeline_rejects_invalid_json_before_loading_config(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()
    issues_path = tmp_path / "issues.json"
    issues_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(PipelineInputError, match="is not valid JSON"):
        AuditPipeline().run(
            PipelineRequest(
                project_path=project_path,
                issues_path=issues_path,
            )
        )

