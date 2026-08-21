"""Legacy role-tagged context assembly used before retrieval is introduced."""
from __future__ import annotations

from dataclasses import dataclass

from app.documents.parsers import ParsedDoc


HELD_OUT_FILENAMES: set[str] = {
    "FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf",
}

FOLDER_TO_TAG = {
    "APM": "APM",
    "AWP": "AWP",
    "Guidelines": "GUIDELINES",
    "Process SOP": "SOP",
    "Process Understanding": "PROCESS_UNDERSTANDING",
    "Samples": "SAMPLES",
}

# Character budget for all tagged blobs combined. ~150k tokens at 4 chars/token,
# leaving headroom for prompt scaffolding inside the 200k-token window.
CHAR_BUDGET = 600_000

# Order to tail-truncate if over budget. Preserve AWP/APM/SCOPE semantics last.
TRUNCATION_ORDER = [
    "SOP", "PROCESS_UNDERSTANDING", "GUIDELINES",
    "SAMPLES", "APM", "AWP",
]


@dataclass
class ContextBlobs:
    blobs: dict[str, str]       # tag -> text (no surrounding <tag>...</tag>)
    truncated: bool
    truncation_log: list[str]   # human-readable lines for run.log


def build_context(parsed: list[ParsedDoc]) -> ContextBlobs:
    """Group parsed artefacts by role tag and concatenate within each group."""
    blobs: dict[str, list[str]] = {tag: [] for tag in FOLDER_TO_TAG.values()}
    for d in parsed:
        if d.filename in HELD_OUT_FILENAMES:
            continue
        tag = FOLDER_TO_TAG.get(d.folder)
        if tag is None:
            continue
        blobs[tag].append(f"### {d.filename}\n{d.text}")

    merged = {tag: "\n\n".join(parts) for tag, parts in blobs.items()}

    total = sum(len(v) for v in merged.values())
    truncation_log: list[str] = []
    if total > CHAR_BUDGET:
        for tag in TRUNCATION_ORDER:
            over = total - CHAR_BUDGET
            if over <= 0:
                break
            original = len(merged[tag])
            merged[tag] = merged[tag][: max(0, original - over)]
            removed = original - len(merged[tag])
            if removed > 0:
                truncation_log.append(
                    f"<{tag}> tail-truncated by {removed:,} chars"
                )
                total -= removed

    return ContextBlobs(
        blobs=merged,
        truncated=bool(truncation_log),
        truncation_log=truncation_log,
    )


def wrap(tag: str, body: str) -> str:
    """Wrap a blob in `<TAG>...</TAG>` for prompt embedding."""
    return f"<{tag}>\n{body}\n</{tag}>"
