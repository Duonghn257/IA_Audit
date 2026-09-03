from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.bootstrap.api import create_app
from docx import Document
from fastapi.testclient import TestClient

from tests.integration.test_discovery_api import _settings

_DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_central_knowledge_upload_overwrite_download_and_delete(
    tmp_path: Path,
) -> None:
    app = create_app(settings=_settings(tmp_path))
    with TestClient(app) as client:
        empty = client.get("/api/v1/central-knowledge")
        assert empty.status_code == 200
        assert empty.json() == {
            "guidelines": [],
            "template": None,
            "ready_for_audit": False,
        }

        invalid_template = client.put(
            "/api/v1/central-knowledge/template",
            files={"file": ("template.pdf", b"not a docx", "application/pdf")},
        )
        assert invalid_template.status_code == 422
        assert invalid_template.json()["error"]["code"] == "INVALID_REQUEST"

        first_bytes = _docx_bytes("Guideline first content")
        first = client.post(
            "/api/v1/central-knowledge/guidelines",
            files={
                "file": (
                    "writing-guideline.docx",
                    first_bytes,
                    _DOCX_CONTENT_TYPE,
                )
            },
        )
        assert first.status_code == 200, first.text
        first_asset = first.json()

        template = client.put(
            "/api/v1/central-knowledge/template",
            files={
                "file": (
                    "template.docx",
                    _docx_bytes("Application template"),
                    _DOCX_CONTENT_TYPE,
                )
            },
        )
        assert template.status_code == 200, template.text

        ready = client.get("/api/v1/central-knowledge").json()
        assert ready["ready_for_audit"] is True
        assert len(ready["guidelines"]) == 1
        assert ready["template"]["filename"] == "template.docx"

        second_bytes = _docx_bytes("Guideline overwritten content")
        overwritten = client.post(
            "/api/v1/central-knowledge/guidelines",
            files={
                "file": (
                    "writing-guideline.docx",
                    second_bytes,
                    _DOCX_CONTENT_TYPE,
                )
            },
        )
        assert overwritten.status_code == 200, overwritten.text
        assert overwritten.json()["asset_id"] == first_asset["asset_id"]
        assert overwritten.json()["content_hash"] != first_asset["content_hash"]
        assert len(client.get("/api/v1/central-knowledge").json()["guidelines"]) == 1

        downloaded = client.get(overwritten.json()["download_url"])
        assert downloaded.status_code == 200
        assert downloaded.content == second_bytes

        deleted = client.delete(
            f"/api/v1/central-knowledge/files/{first_asset['asset_id']}"
        )
        assert deleted.status_code == 204
        after_delete = client.get("/api/v1/central-knowledge").json()
        assert after_delete["guidelines"] == []
        assert after_delete["ready_for_audit"] is False
        missing = client.get(overwritten.json()["download_url"])
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "CENTRAL_ASSET_NOT_FOUND"
    app.state.database.dispose()
