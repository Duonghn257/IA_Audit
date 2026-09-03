from app.documents.parsers import ParsedDoc
from app.rag.context import build_context


def test_project_sample_is_included_in_sample_context() -> None:
    context = build_context(
        [
            ParsedDoc(
                folder="Samples",
                filename=(
                    "FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf"
                ),
                text="Approved prior audit wording",
            )
        ]
    )

    assert "Approved prior audit wording" in context.blobs["SAMPLES"]
