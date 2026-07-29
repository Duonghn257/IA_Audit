from io import BytesIO

import pytest

from app.application.project_files import (
    IncomingProjectFile,
    ProjectUploadError,
)
from app.infrastructure.project_storage import LocalProjectStorage


def test_storage_preserves_folder_tree_and_promotes_output(tmp_path) -> None:
    storage = LocalProjectStorage(
        tmp_path / "storage",
        max_files=10,
        max_total_bytes=1024,
    )

    stored = storage.save_uploads(
        "project-1",
        [
            IncomingProjectFile(
                "Selected Project/APM/apm.txt",
                BytesIO(b"APM"),
            ),
            IncomingProjectFile(
                "Selected Project/sample_issues.json",
                BytesIO(b"[]"),
            ),
        ],
    )

    assert (stored.project_path / "APM" / "apm.txt").read_bytes() == b"APM"
    assert (stored.project_path / "sample_issues.json").is_file()

    generated = stored.project_path / "Output" / "v0.1" / "result.docx"
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"docx")
    promoted = storage.promote_output("project-1", generated)

    storage.delete_raw_input("project-1")

    assert not stored.project_path.exists()
    assert promoted.read_bytes() == b"docx"


def test_storage_rejects_path_traversal(tmp_path) -> None:
    storage = LocalProjectStorage(
        tmp_path / "storage",
        max_files=10,
        max_total_bytes=1024,
    )

    with pytest.raises(ProjectUploadError, match="Unsafe relative path"):
        storage.save_uploads(
            "project-1",
            [IncomingProjectFile("../secret.txt", BytesIO(b"secret"))],
        )

