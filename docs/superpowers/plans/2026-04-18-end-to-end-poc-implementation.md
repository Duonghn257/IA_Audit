# Operation Report Jedi POC Implementation Plan

> **Status (2026-04-22):** This plan is a **historical execution record** — all 20 tasks (0-19) are committed. The pipeline has since been refined to an **8-stage / 4-LLM** flow (adding a Styling step with `src/template_inspector.py` + `src/prompts/styling.py`, a `review_procedures` appendix in `constraints.json`, and `column_aligns` on exception tables in `draft.json`). See `docs/superpowers/specs/2026-04-18-end-to-end-poc-design.md` for the current authoritative flow. Do not treat this file as the current design.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal (as originally scoped):** Ship an end-to-end CLI that parses the Lumina Grand audit project, runs a 3-step LLM chain, and emits a versioned DOCX issue log plus JSON artefacts, matching the design in `docs/superpowers/specs/2026-04-18-end-to-end-poc-design.md`.

**Architecture (as originally scoped):** Procedural pipeline. Pure-ish functions in `src/` modules. `main.py` wires the 7 stages top-to-bottom. JSON files are stage-to-stage handoffs. Always re-parse; never overwrite a prior version directory.

**Tech Stack:** Python 3.11+, `anthropic`, `python-docx`, `pdfplumber`, `openpyxl`, `python-dotenv`. Direct Anthropic API (model `claude-sonnet-4-5`), no AWS/Azure services.

**Testing strategy (per spec §9):** No unit test suite up front. Each task verifies itself with a walking-skeleton run against the real Lumina Grand corpus and an explicit expected-output check. Regression tests are added only when a real bug surfaces.

---

## File Plan

**Create:**
- `src/__init__.py`
- `src/config.py` — loads `.env`, exposes `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` / `ANTHROPIC_URI_ENDPOINT`
- `src/llm.py` — Anthropic client factory, retry wrapper, JSON extraction with single-shot retry
- `src/parsers.py` — `parse_docx`, `parse_pdf`, `parse_xlsx`, `parse_folder`, `persist_parsed`
- `src/context.py` — `HELD_OUT_FILENAMES`, `build_context`, `CHAR_BUDGET` truncation
- `src/prompts/__init__.py`
- `src/prompts/constraints.py` — Step 1 prompt + `extract_constraints()`
- `src/prompts/drafting.py` — Step 2 prompt + `draft_issues()`
- `src/prompts/critique.py` — Step 3 prompt + `critique_draft()`
- `src/validate.py` — `check_evidence_refs`, `check_scope`, `build_validation`
- `src/render.py` — `render(draft, project_name, version, out_path)`
- `src/versioning.py` — `next_version(project_path)`
- `main.py` — CLI entry, wires all 7 stages + `run.log` writer
- `sample_issues.json` — hand-seeded auditor input for Lumina Grand
- `POC_DEMO_NOTES.md` — final comparison notes (filled in Task 18)

**Modify:** none (this is a greenfield POC).

**Rely on existing:** `test_connection.py`, `requirements.txt`, `.env`, `.env.example`, `CLAUDE.md`, `data/lumina_grand/`.

---

## Task 0: Bootstrap git + verify environment

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Initialize git and make it a repo**

The project is currently not a git repo (per CLAUDE.md). Initialize it so each subsequent task can commit.

```bash
git init
git branch -M main
```

- [ ] **Step 2: Write `.gitignore`**

Create `.gitignore`:
```
__pycache__/
*.pyc
.venv/
venv/
.env
data/*/Output/v0.*/
.vscode/
.idea/
.DS_Store
Thumbs.db
```

Rationale: versioned output folders (`v0.N/`) are generated artefacts — they shouldn't bloat history. The approved `.env` stays local; only `.env.example` is tracked.

- [ ] **Step 3: Verify Python deps are installed**

Run:
```bash
python -c "import anthropic, docx, pdfplumber, openpyxl, dotenv; print('ok')"
```
Expected: `ok`. If it fails, run `pip install -r requirements.txt` first.

- [ ] **Step 4: Verify the API smoke test passes**

Run:
```bash
python test_connection.py
```
Expected output contains `Connection OK.` and a non-empty `Response :` line. If it fails, stop — `.env` is not configured; no later task can succeed.

- [ ] **Step 5: Initial commit**

```bash
git add .gitignore requirements.txt test_connection.py .env.example CLAUDE.md docs/
git commit -m "chore: initial commit — specs, env, smoke test"
```

---

## Task 1: Project skeleton

**Files:**
- Create: `src/__init__.py`, `src/prompts/__init__.py`
- Create: empty module files for all `src/` modules listed in File Plan
- Create: `main.py` (argparse skeleton only)

- [ ] **Step 1: Create `src/` package**

```bash
mkdir -p src/prompts
```

Create `src/__init__.py` with content:
```python
"""Operation Report Jedi — POC pipeline."""
```

Create `src/prompts/__init__.py` with content:
```python
"""Prompt modules for the 3-step LLM chain."""
```

- [ ] **Step 2: Create empty module placeholders**

Each of these files must exist but start with only a one-line module docstring so imports work. Create:

`src/config.py`:
```python
"""Environment loading for Anthropic credentials."""
```

`src/llm.py`:
```python
"""Anthropic client wrapper, retry, and JSON extraction."""
```

`src/parsers.py`:
```python
"""Local document parsers: DOCX, PDF, XLSX."""
```

`src/context.py`:
```python
"""Role-tagged context assembly with hold-out and truncation."""
```

`src/prompts/constraints.py`:
```python
"""Step 1 — constraint extraction from AWP + APM."""
```

`src/prompts/drafting.py`:
```python
"""Step 2 — draft issues from auditor input + artefacts."""
```

`src/prompts/critique.py`:
```python
"""Step 3 — LLM self-critique of the draft."""
```

`src/validate.py`:
```python
"""Rule-based validation checks."""
```

`src/render.py`:
```python
"""DOCX renderer."""
```

`src/versioning.py`:
```python
"""Output version directory scanner."""
```

- [ ] **Step 3: Write `main.py` with argparse skeleton**

Create `main.py`:
```python
"""Operation Report Jedi — CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Draft an Internal Audit issue log from a project folder.",
    )
    p.add_argument(
        "--project",
        required=True,
        type=Path,
        help="Path to the project root (containing APM/, AWP/, etc.).",
    )
    p.add_argument(
        "--issues",
        required=True,
        type=Path,
        help="Path to sample_issues.json.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.project.is_dir():
        print(f"ERROR: --project {args.project} is not a directory", file=sys.stderr)
        return 1
    if not args.issues.is_file():
        print(f"ERROR: --issues {args.issues} is not a file", file=sys.stderr)
        return 1
    print(f"Project : {args.project}")
    print(f"Issues  : {args.issues}")
    print("Pipeline not yet wired — skeleton only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Walking-skeleton verify**

Run:
```bash
python main.py --project data/lumina_grand --issues /nonexistent.json
```
Expected: `ERROR: --issues /nonexistent.json is not a file` and exit code 1.

Run:
```bash
touch /tmp/dummy.json
python main.py --project data/lumina_grand --issues /tmp/dummy.json
echo "exit=$?"
```
Expected: prints the two paths + `Pipeline not yet wired — skeleton only.` and `exit=0`.

Clean up: `rm /tmp/dummy.json`.

- [ ] **Step 5: Commit**

```bash
git add src/ main.py
git commit -m "feat: scaffold src/ package and CLI skeleton"
```

---

## Task 2: `src/config.py` — environment loader

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Write the config module**

Replace `src/config.py` contents with:
```python
"""Environment loading for Anthropic credentials."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    base_url: str | None  # None → SDK default


def load_config() -> Config:
    """Load and validate Anthropic config from .env. Exits 1 on missing vars."""
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL")
    endpoint = os.environ.get("ANTHROPIC_URI_ENDPOINT") or None

    missing = [n for n, v in {"ANTHROPIC_API_KEY": api_key,
                              "ANTHROPIC_MODEL": model}.items() if not v]
    if missing:
        print(f"ERROR: missing required env var(s): {', '.join(missing)}",
              file=sys.stderr)
        sys.exit(1)

    # Azure AI Foundry publishes endpoints with '/v1/messages' already appended.
    # The Anthropic SDK appends it itself, so strip the suffix to avoid doubling.
    if endpoint:
        for suffix in ("/v1/messages", "/v1/messages/"):
            if endpoint.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                break

    return Config(api_key=api_key, model=model, base_url=endpoint)
```

- [ ] **Step 2: Walking-skeleton verify**

Run:
```bash
python -c "from src.config import load_config; c = load_config(); print(f'model={c.model} base_url={c.base_url}')"
```
Expected: prints `model=claude-sonnet-4-5 base_url=...` (or `base_url=None` if `ANTHROPIC_URI_ENDPOINT` is unset). No traceback, no stderr.

- [ ] **Step 3: Commit**

```bash
git add src/config.py
git commit -m "feat(config): load Anthropic env vars with Azure endpoint normalization"
```

---

## Task 3: `src/llm.py` — client wrapper + retry + JSON extraction

**Files:**
- Modify: `src/llm.py`

- [ ] **Step 1: Write the LLM module**

Replace `src/llm.py` contents with:
```python
"""Anthropic client wrapper, retry, and JSON extraction."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import anthropic

from .config import Config


@dataclass
class LLMResult:
    data: Any              # parsed JSON (dict or list)
    input_tokens: int
    output_tokens: int
    raw_text: str


def make_client(cfg: Config) -> anthropic.Anthropic:
    kwargs: dict[str, Any] = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return anthropic.Anthropic(**kwargs)


def _call_with_retry(
    client: anthropic.Anthropic,
    *,
    max_attempts: int = 3,
    **kwargs: Any,
) -> anthropic.types.Message:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            last_err = e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                last_err = e
            else:
                raise
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
    assert last_err is not None
    raise last_err


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _strip_fence(text: str) -> str:
    """Extract JSON from a fenced block, or return text unchanged."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    # Fallback: find first balanced { or [
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return text.strip()


def _text_of(resp: anthropic.types.Message) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def call_json(
    client: anthropic.Anthropic,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> LLMResult:
    """Send a messages.create call and parse a JSON response, with one retry on bad JSON."""
    messages = [{"role": "user", "content": user}]
    resp = _call_with_retry(
        client, model=model, system=system, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    text = _text_of(resp)
    try:
        data = json.loads(_strip_fence(text))
    except json.JSONDecodeError:
        # One-shot retry with a reminder
        messages = [
            {"role": "user", "content": user},
            {"role": "assistant", "content": text},
            {"role": "user", "content":
             "Your previous reply was not valid JSON. "
             "Respond with JSON only, inside a ```json fenced block."},
        ]
        resp = _call_with_retry(
            client, model=model, system=system, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        text = _text_of(resp)
        data = json.loads(_strip_fence(text))

    return LLMResult(
        data=data,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        raw_text=text,
    )
```

- [ ] **Step 2: Walking-skeleton verify — offline parts**

Run:
```bash
python -c "from src.llm import _strip_fence; print(repr(_strip_fence('foo \`\`\`json\n{\"a\": 1}\n\`\`\` bar')))"
```
Expected: `'{"a": 1}'` (exact quotes may differ; the point is no `foo` / `bar` and the JSON body only).

Run:
```bash
python -c "from src.llm import _strip_fence; print(repr(_strip_fence('prefix {\"a\": [1,2]} suffix')))"
```
Expected: `'{"a": [1,2]}'`.

- [ ] **Step 3: Walking-skeleton verify — live call**

Run:
```bash
python -c "
from src.config import load_config
from src.llm import make_client, call_json
cfg = load_config()
client = make_client(cfg)
r = call_json(client, model=cfg.model,
              system='You reply with JSON.',
              user='Return {\"hello\": \"world\"} inside a json fence.',
              max_tokens=128, temperature=0.0)
print('data=', r.data)
print('tokens in/out=', r.input_tokens, '/', r.output_tokens)
"
```
Expected: `data= {'hello': 'world'}` and a non-zero tokens line. If this fails with a 401/403, `.env` credentials are wrong — stop here.

- [ ] **Step 4: Commit**

```bash
git add src/llm.py
git commit -m "feat(llm): Anthropic wrapper with retry and JSON extraction"
```

---

## Task 4: `src/parsers.py` — DOCX parser

**Files:**
- Modify: `src/parsers.py`

- [ ] **Step 1: Write `parse_docx`**

Replace `src/parsers.py` contents with:
```python
"""Local document parsers: DOCX, PDF, XLSX."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDoc:
    folder: str       # e.g. "APM", "AWP", "Samples"
    filename: str     # original basename, e.g. "Lumina Grand_2. APM (8 Mar) (V3).docx"
    text: str         # extracted text, lightly Markdown-ish


def parse_docx(path: Path) -> str:
    """Extract paragraphs and tables from a .docx as plain text / light Markdown."""
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = []
    for para in doc.paragraphs:
        t = para.text.strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        parts.append("")  # blank line before table
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            parts.append("| " + " | ".join(cells) + " |")
    return "\n".join(parts).strip()
```

- [ ] **Step 2: Walking-skeleton verify — APM parses**

Run:
```bash
python -c "
from pathlib import Path
from src.parsers import parse_docx
t = parse_docx(Path('data/lumina_grand/APM/Lumina Grand_2. APM (8 Mar) (V3).docx'))
print('chars:', len(t))
print('--- first 500 chars ---')
print(t[:500])
"
```
Expected: `chars:` between 5,000 and 80,000 (APM is ~396KB on disk but extracted text is smaller); the first 500 chars contain readable prose with no raw XML. If you see `<w:` tags, something's wrong with `python-docx`.

- [ ] **Step 3: Commit**

```bash
git add src/parsers.py
git commit -m "feat(parsers): DOCX extraction with paragraph + table flattening"
```

---

## Task 5: `src/parsers.py` — PDF parser

**Files:**
- Modify: `src/parsers.py`

- [ ] **Step 1: Add `parse_pdf`**

Append to `src/parsers.py`:
```python
def parse_pdf(path: Path) -> str:
    """Extract text from a .pdf using pdfplumber, one block per page."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i} ---\n{text.strip()}")
    return "\n\n".join(pages).strip()
```

- [ ] **Step 2: Walking-skeleton verify — Guidelines PDF parses**

Run:
```bash
python -c "
from pathlib import Path
from src.parsers import parse_pdf
t = parse_pdf(Path('data/lumina_grand/Guidelines/Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf'))
print('chars:', len(t))
print('pages:', t.count('--- Page '))
print('--- first 500 chars ---')
print(t[:500])
"
```
Expected: `chars:` > 2,000, `pages:` > 0, first 500 chars contain English prose about formatting / tone.

- [ ] **Step 3: Commit**

```bash
git add src/parsers.py
git commit -m "feat(parsers): PDF extraction with page separators"
```

---

## Task 6: `src/parsers.py` — XLSX parser

**Files:**
- Modify: `src/parsers.py`

- [ ] **Step 1: Add `parse_xlsx`**

Append to `src/parsers.py`:
```python
def parse_xlsx(path: Path) -> str:
    """Extract each sheet of a .xlsx as a Markdown-ish table."""
    from openpyxl import load_workbook

    wb = load_workbook(str(path), data_only=True, read_only=True)
    parts: list[str] = []
    for sheet in wb.worksheets:
        parts.append(f"## Sheet: {sheet.title}")
        rows_iter = sheet.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            continue
        header_cells = [str(c) if c is not None else "" for c in header]
        parts.append("| " + " | ".join(header_cells) + " |")
        parts.append("| " + " | ".join(["---"] * len(header_cells)) + " |")
        for row in rows_iter:
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                parts.append("| " + " | ".join(cells) + " |")
        parts.append("")
    return "\n".join(parts).strip()
```

- [ ] **Step 2: Walking-skeleton verify — Access Rights XLSX parses**

Run:
```bash
python -c "
from pathlib import Path
from src.parsers import parse_xlsx
t = parse_xlsx(Path('data/lumina_grand/Process Understanding/PD_Roles_AccessRights_22Mar2024.xlsx'))
print('chars:', len(t))
print('sheets:', t.count('## Sheet:'))
print('--- first 800 chars ---')
print(t[:800])
"
```
Expected: `sheets:` >= 1, a Markdown-style table visible in the first 800 chars, column headers reading like role/access terminology.

- [ ] **Step 3: Commit**

```bash
git add src/parsers.py
git commit -m "feat(parsers): XLSX extraction with per-sheet Markdown tables"
```

---

## Task 7: `src/parsers.py` — `parse_folder` + `persist_parsed`

**Files:**
- Modify: `src/parsers.py`

- [ ] **Step 1: Add `parse_folder` and `persist_parsed`**

Append to `src/parsers.py`:
```python
PARSERS_BY_EXT = {
    ".docx": parse_docx,
    ".pdf": parse_pdf,
    ".xlsx": parse_xlsx,
}

ARTEFACT_FOLDERS = [
    "APM", "AWP", "Guidelines",
    "Process SOP", "Process Understanding", "Samples",
]


def parse_folder(project_root: Path, skip_filenames: set[str] | None = None) -> list[ParsedDoc]:
    """Parse every known-extension file in each artefact folder.

    Files whose basename appears in `skip_filenames` are still discovered
    but not parsed or returned (they are held out from downstream stages).
    Unknown extensions are silently skipped. Parse failures are re-raised
    with the offending path for the caller to log.
    """
    skip = skip_filenames or set()
    out: list[ParsedDoc] = []
    for folder in ARTEFACT_FOLDERS:
        fdir = project_root / folder
        if not fdir.is_dir():
            continue
        for p in sorted(fdir.iterdir()):
            if not p.is_file():
                continue
            if p.name in skip:
                continue
            parser = PARSERS_BY_EXT.get(p.suffix.lower())
            if parser is None:
                continue
            try:
                text = parser(p)
            except Exception as e:
                raise RuntimeError(f"failed to parse {p}: {e}") from e
            out.append(ParsedDoc(folder=folder, filename=p.name, text=text))
    return out


def persist_parsed(parsed: list[ParsedDoc], out_root: Path) -> None:
    """Write each ParsedDoc to `<out_root>/parsed/<folder>/<basename>.md`."""
    for d in parsed:
        target_dir = out_root / "parsed" / d.folder
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(d.filename).stem
        (target_dir / f"{stem}.md").write_text(d.text, encoding="utf-8")
```

- [ ] **Step 2: Walking-skeleton verify — full parse + persist**

Run:
```bash
python -c "
from pathlib import Path
from src.parsers import parse_folder, persist_parsed
held_out = {'FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf'}
parsed = parse_folder(Path('data/lumina_grand'), skip_filenames=held_out)
print('files parsed:', len(parsed))
for d in parsed:
    print(f'  [{d.folder}] {d.filename} ({len(d.text)} chars)')
persist_parsed(parsed, Path('/tmp/parse_smoke'))
import subprocess
print(subprocess.check_output(['find', '/tmp/parse_smoke/parsed', '-type', 'f']).decode())
"
```
Expected:
- `files parsed: 8` (2 DOCX in APM+AWP, 1 PDF + 2 PDF in Process SOP, 1 DOCX + 1 XLSX in Process Understanding, 1 DOCX in Samples — the FY2024 PDF is held out).
- Each listed file has > 500 chars.
- `find` output shows 8 `.md` files under `/tmp/parse_smoke/parsed/` grouped by folder.

Clean up: `rm -rf /tmp/parse_smoke`.

- [ ] **Step 3: Commit**

```bash
git add src/parsers.py
git commit -m "feat(parsers): folder traversal and parsed artefact persistence"
```

---

## Task 8: `src/context.py` — role-tagged assembly + hold-out + truncation

**Files:**
- Modify: `src/context.py`

- [ ] **Step 1: Write the context module**

Replace `src/context.py` contents with:
```python
"""Role-tagged context assembly with hold-out and truncation."""
from __future__ import annotations

from dataclasses import dataclass

from .parsers import ParsedDoc


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
```

- [ ] **Step 2: Walking-skeleton verify — sizes and hold-out**

Run:
```bash
python -c "
from pathlib import Path
from src.parsers import parse_folder
from src.context import build_context, HELD_OUT_FILENAMES
parsed = parse_folder(Path('data/lumina_grand'), skip_filenames=HELD_OUT_FILENAMES)
ctx = build_context(parsed)
for tag, body in ctx.blobs.items():
    print(f'<{tag}> {len(body):,} chars')
print('total:', sum(len(v) for v in ctx.blobs.values()), 'chars')
print('truncated:', ctx.truncated)
print('SAMPLES contains FY2024?', 'FY2024' in ctx.blobs['SAMPLES'])
"
```
Expected:
- Each of 6 tags has >0 chars.
- `total:` comfortably under 600,000.
- `truncated: False`.
- `SAMPLES contains FY2024? False` — hold-out is working.

- [ ] **Step 3: Commit**

```bash
git add src/context.py
git commit -m "feat(context): role-tagged assembly with FY2024 hold-out and truncation"
```

---

## Task 9: `src/versioning.py` — next version directory

**Files:**
- Modify: `src/versioning.py`

- [ ] **Step 1: Write the versioning module**

Replace `src/versioning.py` contents with:
```python
"""Output version directory scanner."""
from __future__ import annotations

import re
from pathlib import Path

_VERSION_RE = re.compile(r"^v0\.(\d+)$")


def next_version(project_path: Path) -> tuple[str, Path]:
    """Return (version_name, run_dir) for a new run.

    Scans `<project>/Output/` for existing `v0.N/` directories, picks N+1,
    and creates the new directory. Never overwrites an existing version.
    Non-directory files at the Output root (e.g., legacy `.docx` drafts from
    older runs) are ignored.
    """
    output_root = project_path / "Output"
    output_root.mkdir(exist_ok=True)
    existing = [
        int(m.group(1))
        for d in output_root.iterdir()
        if d.is_dir() and (m := _VERSION_RE.match(d.name))
    ]
    n = (max(existing) + 1) if existing else 1
    version = f"v0.{n}"
    run_dir = output_root / version
    run_dir.mkdir()
    return version, run_dir
```

- [ ] **Step 2: Walking-skeleton verify — two successive calls**

Run:
```bash
python -c "
from pathlib import Path
import shutil, tempfile
from src.versioning import next_version
tmp = Path(tempfile.mkdtemp())
print(next_version(tmp))
print(next_version(tmp))
(tmp / 'Output' / 'v0.2' / 'dummy.txt').write_text('x')
print(next_version(tmp))  # should be v0.3
shutil.rmtree(tmp)
"
```
Expected output (paths will differ):
```
('v0.1', <tmp>/Output/v0.1)
('v0.2', <tmp>/Output/v0.2)
('v0.3', <tmp>/Output/v0.3)
```

- [ ] **Step 3: Commit**

```bash
git add src/versioning.py
git commit -m "feat(versioning): next v0.N directory allocator"
```

---

## Task 10: `src/prompts/constraints.py` — Step 1 LLM call

**Files:**
- Modify: `src/prompts/constraints.py`

- [ ] **Step 1: Write the constraints prompt module**

Replace `src/prompts/constraints.py` contents with:
```python
"""Step 1 — constraint extraction from AWP + APM."""
from __future__ import annotations

from typing import Any

import anthropic

from ..llm import LLMResult, call_json

SYSTEM = (
    "You are an Internal Audit scope extractor. You read an Approved Work "
    "Program (AWP) and Approved Planning Memo (APM) for a single audit "
    "engagement and emit a structured scope envelope. You do not invent "
    "scope items or entities not present in the inputs."
)

USER_TEMPLATE = """<AWP>
{awp}
</AWP>

<APM>
{apm}
</APM>

Return a single JSON object matching this schema:
{{
  "audit_scope": "<one-paragraph description>",
  "audited_entities": ["<entity>", ...],
  "key_risks": ["<risk statement>", ...],
  "out_of_scope_items": ["<item>", ...]
}}

Rules:
- Only include entities named in the AWP or APM.
- key_risks must reflect the APM's stated risk focus, not generic audit risks.
- If out-of-scope items are not explicitly stated, return an empty array.

Respond with JSON only, inside a ```json fenced block."""


def extract_constraints(
    client: anthropic.Anthropic,
    model: str,
    awp: str,
    apm: str,
) -> LLMResult:
    user = USER_TEMPLATE.format(awp=awp, apm=apm)
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=2048, temperature=0.2,
    )
```

- [ ] **Step 2: Walking-skeleton verify — live Step 1 on Lumina Grand**

Run:
```bash
python -c "
from pathlib import Path
import json
from src.config import load_config
from src.llm import make_client
from src.parsers import parse_folder
from src.context import build_context, HELD_OUT_FILENAMES
from src.prompts.constraints import extract_constraints

cfg = load_config()
client = make_client(cfg)
parsed = parse_folder(Path('data/lumina_grand'), skip_filenames=HELD_OUT_FILENAMES)
ctx = build_context(parsed)
res = extract_constraints(client, cfg.model, awp=ctx.blobs['AWP'], apm=ctx.blobs['APM'])
print('tokens in/out:', res.input_tokens, '/', res.output_tokens)
print(json.dumps(res.data, indent=2)[:1500])
"
```
Expected:
- Valid JSON printed with all four keys (`audit_scope`, `audited_entities`, `key_risks`, `out_of_scope_items`).
- `audit_scope` mentions PDPA (the audit is a PDPA audit).
- `audited_entities` contains at least one entity resembling "CDL Zenith" or "Lumina Grand".
- No tracebacks.

If `audit_scope` is blank or entities are wrong, the prompt may need a minor tweak — but do that tweak in the same task and rerun before committing.

- [ ] **Step 3: Commit**

```bash
git add src/prompts/constraints.py
git commit -m "feat(prompts): Step 1 — constraint extraction from AWP+APM"
```

---

## Task 11: `sample_issues.json` — hand-seeded auditor input

**Files:**
- Create: `sample_issues.json`

- [ ] **Step 1: Read the FY2024 approved report to identify 2–3 real findings**

Run:
```bash
python -c "
import pdfplumber
path = 'data/lumina_grand/Samples/FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf'
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages, start=1):
        t = page.extract_text() or ''
        if t.strip():
            print(f'--- Page {i} ---')
            print(t)
            print()
" | head -300
```
Read the output. Identify 2–3 distinct audit findings (look for phrases like "observed", "noted", "recommendation"). Capture for each: the gap, the evidence source, the SOP / policy section it cites.

- [ ] **Step 2: Write `sample_issues.json`**

Create `sample_issues.json` with the shape below. **Replace the three example entries with findings from the FY2024 PDF you read in Step 1.** Keep to 2–3 entries; more is fine, but the first smoke run should stay small to save tokens.

```json
[
  {
    "title_hint": "<short phrase describing the gap — e.g., 'Annual PDPA training coverage'>",
    "observed_gap": "<2–3 sentence auditor description of the deviation>",
    "evidence_summary": "<specific evidence: figures, sample sizes, filenames>",
    "evidence_refs": [
      "<cite the source: e.g., 'HR-LMS export 2024-Q3'>",
      "<cite the SOP clause: e.g., 'CDL PDPA Manual §4.2'>"
    ],
    "sop_refs": ["<SOP section that was deviated from>"],
    "risk_category": "<one of: Compliance | Operational | Strategic | Financial>"
  },
  {
    "title_hint": "...",
    "observed_gap": "...",
    "evidence_summary": "...",
    "evidence_refs": ["...", "..."],
    "sop_refs": ["..."],
    "risk_category": "..."
  }
]
```

Validate the JSON:
```bash
python -c "import json; print(len(json.load(open('sample_issues.json'))), 'issues')"
```
Expected: `2 issues` or `3 issues`.

- [ ] **Step 3: Commit**

```bash
git add sample_issues.json
git commit -m "feat: seed sample_issues.json from FY2024 Lumina Grand findings"
```

---

## Task 12: `src/prompts/drafting.py` — Step 2 LLM call

**Files:**
- Modify: `src/prompts/drafting.py`

- [ ] **Step 1: Write the drafting prompt module**

Replace `src/prompts/drafting.py` contents with:
```python
"""Step 2 — draft issues from auditor input + artefacts."""
from __future__ import annotations

import json
from typing import Any

import anthropic

from ..context import wrap
from ..llm import LLMResult, call_json

SYSTEM = (
    "You are an Internal Audit issue-log drafter. You draft professional "
    "audit issues from auditor-provided observations, staying strictly "
    "within the audit scope and citing only evidence from supplied "
    "artefacts. You write in a constructive, positive-title house style. "
    "You are a drafting assistant — you do not invent findings, recommend "
    "beyond evidence, or expand scope."
)

USER_TEMPLATE = """{scope_block}

{guidelines_block}

{samples_block}

{sop_block}

{pu_block}

{auditor_input_block}

For EACH item in <AUDITOR_INPUT>, produce one issue. Output a JSON array:
[{{"id": "I-1", "title": "...", "finding": "...",
  "impact": "...", "recommendation": "...",
  "evidence_refs": ["..."]}}]

Rules:
- N in = N out. Preserve order.
- Titles must be positive-framed per <GUIDELINES>.
- Every issue must stay within audit_scope and audited_entities in <SCOPE>.
- evidence_refs must cite <PROCESS_UNDERSTANDING> or <SOP> passages; do not fabricate.
- Tone and section structure must match <SAMPLES> (the empty Issue Log Template).

Respond with JSON only, inside a ```json fenced block."""


def draft_issues(
    client: anthropic.Anthropic,
    model: str,
    *,
    constraints: dict[str, Any],
    guidelines: str,
    samples: str,
    sop: str,
    process_understanding: str,
    auditor_input: list[dict[str, Any]],
) -> LLMResult:
    user = USER_TEMPLATE.format(
        scope_block=wrap("SCOPE", json.dumps(constraints, indent=2)),
        guidelines_block=wrap("GUIDELINES", guidelines),
        samples_block=wrap("SAMPLES", samples),
        sop_block=wrap("SOP", sop),
        pu_block=wrap("PROCESS_UNDERSTANDING", process_understanding),
        auditor_input_block=wrap(
            "AUDITOR_INPUT", json.dumps(auditor_input, indent=2)
        ),
    )
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=4096, temperature=0.4,
    )
```

- [ ] **Step 2: Walking-skeleton verify — live Step 2 on Lumina Grand**

Run:
```bash
python -c "
import json
from pathlib import Path
from src.config import load_config
from src.llm import make_client
from src.parsers import parse_folder
from src.context import build_context, HELD_OUT_FILENAMES
from src.prompts.constraints import extract_constraints
from src.prompts.drafting import draft_issues

cfg = load_config()
client = make_client(cfg)
parsed = parse_folder(Path('data/lumina_grand'), skip_filenames=HELD_OUT_FILENAMES)
ctx = build_context(parsed)

c = extract_constraints(client, cfg.model, awp=ctx.blobs['AWP'], apm=ctx.blobs['APM']).data
auditor = json.load(open('sample_issues.json'))

d = draft_issues(
    client, cfg.model,
    constraints=c,
    guidelines=ctx.blobs['GUIDELINES'],
    samples=ctx.blobs['SAMPLES'],
    sop=ctx.blobs['SOP'],
    process_understanding=ctx.blobs['PROCESS_UNDERSTANDING'],
    auditor_input=auditor,
)
print('tokens in/out:', d.input_tokens, '/', d.output_tokens)
print('issues drafted:', len(d.data))
print(json.dumps(d.data[0], indent=2))
"
```
Expected:
- `issues drafted:` equals the number of entries in `sample_issues.json`.
- Each issue has non-empty `id`, `title`, `finding`, `impact`, `recommendation`, and `evidence_refs`.
- `id` starts with `I-`.
- The first issue's title reads like an audit-report heading (not a bulleted note).

- [ ] **Step 3: Commit**

```bash
git add src/prompts/drafting.py
git commit -m "feat(prompts): Step 2 — issue drafting with scope + role-tagged context"
```

---

## Task 13: `src/prompts/critique.py` — Step 3 LLM call

**Files:**
- Modify: `src/prompts/critique.py`

- [ ] **Step 1: Write the critique prompt module**

Replace `src/prompts/critique.py` contents with:
```python
"""Step 3 — LLM self-critique of the draft."""
from __future__ import annotations

import json
from typing import Any

import anthropic

from ..context import wrap
from ..llm import LLMResult, call_json

SYSTEM = (
    "You are an Internal Audit reviewer. You inspect a draft issue log "
    "against the audit scope, writing guidelines, and source evidence. "
    "You flag issues — you do not rewrite them. Be specific: quote the "
    "exact problematic excerpt."
)

USER_TEMPLATE = """{scope_block}

{guidelines_block}

{sop_block}

{pu_block}

{draft_block}

Review each issue in <DRAFT>. Return JSON:
{{
  "issues": [
    {{"issue_id": "I-1",
     "flags": [
       {{"type": "SCOPE_BREACH" | "UNSUPPORTED_ASSERTION"
              | "TONE_VIOLATION"  | "WEAK_EVIDENCE",
        "severity": "low" | "medium" | "high",
        "excerpt": "<verbatim text from the draft>",
        "reason": "<one sentence>"}}
     ]}}
  ],
  "summary": "<2-3 sentence overall assessment>"
}}

Flag types:
- SCOPE_BREACH: content references entities or activities outside <SCOPE>.
- UNSUPPORTED_ASSERTION: claim cannot be traced to <SOP> or <PROCESS_UNDERSTANDING>.
- TONE_VIOLATION: title or phrasing conflicts with <GUIDELINES>.
- WEAK_EVIDENCE: evidence_refs exist but do not substantiate the finding.

If an issue is clean, return "flags": [].

Respond with JSON only, inside a ```json fenced block."""


def critique_draft(
    client: anthropic.Anthropic,
    model: str,
    *,
    constraints: dict[str, Any],
    guidelines: str,
    sop: str,
    process_understanding: str,
    draft: list[dict[str, Any]],
) -> LLMResult:
    user = USER_TEMPLATE.format(
        scope_block=wrap("SCOPE", json.dumps(constraints, indent=2)),
        guidelines_block=wrap("GUIDELINES", guidelines),
        sop_block=wrap("SOP", sop),
        pu_block=wrap("PROCESS_UNDERSTANDING", process_understanding),
        draft_block=wrap("DRAFT", json.dumps(draft, indent=2)),
    )
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=2048, temperature=0.1,
    )
```

- [ ] **Step 2: Walking-skeleton verify — live Step 3 using saved Step 2 output**

This step reuses the draft produced in Task 12. Simplest path — re-run the full chain end-to-end:

```bash
python -c "
import json
from pathlib import Path
from src.config import load_config
from src.llm import make_client
from src.parsers import parse_folder
from src.context import build_context, HELD_OUT_FILENAMES
from src.prompts.constraints import extract_constraints
from src.prompts.drafting import draft_issues
from src.prompts.critique import critique_draft

cfg = load_config()
client = make_client(cfg)
parsed = parse_folder(Path('data/lumina_grand'), skip_filenames=HELD_OUT_FILENAMES)
ctx = build_context(parsed)
c = extract_constraints(client, cfg.model, awp=ctx.blobs['AWP'], apm=ctx.blobs['APM']).data
auditor = json.load(open('sample_issues.json'))
draft = draft_issues(
    client, cfg.model,
    constraints=c,
    guidelines=ctx.blobs['GUIDELINES'],
    samples=ctx.blobs['SAMPLES'],
    sop=ctx.blobs['SOP'],
    process_understanding=ctx.blobs['PROCESS_UNDERSTANDING'],
    auditor_input=auditor,
).data
r = critique_draft(
    client, cfg.model,
    constraints=c,
    guidelines=ctx.blobs['GUIDELINES'],
    sop=ctx.blobs['SOP'],
    process_understanding=ctx.blobs['PROCESS_UNDERSTANDING'],
    draft=draft,
)
print('tokens in/out:', r.input_tokens, '/', r.output_tokens)
print(json.dumps(r.data, indent=2))
"
```
Expected:
- Top-level JSON has `issues: [...]` and `summary: "..."`.
- `issues` has one entry per draft issue (each with `issue_id` starting `I-` and a `flags` array that may be empty).
- `summary` is a 2–3 sentence string.

- [ ] **Step 3: Commit**

```bash
git add src/prompts/critique.py
git commit -m "feat(prompts): Step 3 — LLM self-critique with flag schema"
```

---

## Task 14: `src/validate.py` — rule-based checks + merge

**Files:**
- Modify: `src/validate.py`

- [ ] **Step 1: Write the validate module**

Replace `src/validate.py` contents with:
```python
"""Rule-based validation checks."""
from __future__ import annotations

from typing import Any


def check_evidence_refs(draft: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for issue in draft:
        refs = issue.get("evidence_refs") or []
        iid = issue.get("id", "?")
        if not refs:
            warnings.append(f"{iid}: missing evidence_refs")
            continue
        if any(not str(r).strip() for r in refs):
            warnings.append(f"{iid}: empty evidence_refs entry")
    return warnings


def check_scope(
    draft: list[dict[str, Any]],
    constraints: dict[str, Any],
) -> list[str]:
    entities = {e.lower() for e in constraints.get("audited_entities", [])}
    out_of_scope = {i.lower() for i in constraints.get("out_of_scope_items", [])}
    warnings: list[str] = []
    for issue in draft:
        iid = issue.get("id", "?")
        blob = " ".join([
            issue.get("title", ""),
            issue.get("finding", ""),
            issue.get("impact", ""),
            issue.get("recommendation", ""),
        ]).lower()
        for term in out_of_scope:
            if term and term in blob:
                warnings.append(
                    f"{iid}: mentions out-of-scope item '{term}'"
                )
        if entities and not any(e in blob for e in entities):
            warnings.append(
                f"{iid}: no audited_entity mentioned (possible scope drift)"
            )
    return warnings


def build_validation(
    draft: list[dict[str, Any]],
    constraints: dict[str, Any],
    llm_critique: dict[str, Any],
    context_truncated: bool,
) -> dict[str, Any]:
    """Assemble the merged validation.json payload."""
    warnings = check_evidence_refs(draft) + check_scope(draft, constraints)
    return {
        "context_truncated": context_truncated,
        "rule_based": {
            "passed": len(warnings) == 0,
            "warnings": warnings,
        },
        "llm_critique": llm_critique,
    }
```

- [ ] **Step 2: Walking-skeleton verify — synthetic draft**

Run:
```bash
python -c "
from src.validate import build_validation
draft = [
  {'id': 'I-1', 'title': 'Good one mentioning CDL Zenith',
   'finding': 'x', 'impact': 'y', 'recommendation': 'z',
   'evidence_refs': ['ref A']},
  {'id': 'I-2', 'title': 'Bad one — mentions IT infrastructure',
   'finding': '', 'impact': '', 'recommendation': '',
   'evidence_refs': []},
]
constraints = {
  'audited_entities': ['CDL Zenith'],
  'out_of_scope_items': ['IT infrastructure'],
}
crit = {'issues': [], 'summary': 'mock'}
import json
print(json.dumps(build_validation(draft, constraints, crit, False), indent=2))
"
```
Expected warnings in output:
- `I-2: missing evidence_refs`
- `I-2: mentions out-of-scope item 'it infrastructure'`
- `I-2: no audited_entity mentioned (possible scope drift)`

And `rule_based.passed: false`.

- [ ] **Step 3: Commit**

```bash
git add src/validate.py
git commit -m "feat(validate): rule-based checks + merged validation payload"
```

---

## Task 15: `src/render.py` — DOCX renderer

**Files:**
- Modify: `src/render.py`

- [ ] **Step 1: Write the render module**

Replace `src/render.py` contents with:
```python
"""DOCX renderer."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Cm, Pt


def render(
    draft: list[dict[str, Any]],
    project_name: str,
    version: str,
    out_path: Path,
) -> None:
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    doc.add_heading(f"{project_name} – Issue Log {version}", level=1)

    for issue in draft:
        iid = issue.get("id", "?")
        title = issue.get("title", "")
        doc.add_heading(f"Issue {iid}: {title}", level=2)

        table = doc.add_table(rows=4, cols=2)
        table.style = "Table Grid"
        for row in table.rows:
            row.cells[0].width = Cm(4)

        evidence_refs = issue.get("evidence_refs") or []
        rows = [
            ("Finding", issue.get("finding", "")),
            ("Impact", issue.get("impact", "")),
            ("Recommendation", issue.get("recommendation", "")),
            ("Evidence", "\n".join(f"• {r}" for r in evidence_refs)),
        ]
        for i, (label, body) in enumerate(rows):
            table.cell(i, 0).text = label
            table.cell(i, 1).text = body

        doc.add_paragraph()  # spacer

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
```

- [ ] **Step 2: Walking-skeleton verify — render a small synthetic draft**

Run:
```bash
python -c "
from pathlib import Path
from src.render import render
draft = [
  {'id': 'I-1', 'title': 'Strengthening PDPA training coverage',
   'finding': 'Review of HR-LMS records noted 13% non-completion.',
   'impact': 'Increases risk of PDPA breach.',
   'recommendation': 'HR to institute quarterly tracking cadence.',
   'evidence_refs': ['HR-LMS 2024-Q3', 'CDL PDPA Manual §4.2']},
]
out = Path('/tmp/render_smoke.docx')
render(draft, project_name='Lumina Grand', version='v0.1', out_path=out)
print('wrote', out, out.stat().st_size, 'bytes')
"
```
Expected: `/tmp/render_smoke.docx` exists and is > 5,000 bytes. Open it in Word (or LibreOffice) and verify:
- Title reads `Lumina Grand – Issue Log v0.1`.
- One heading `Issue I-1: Strengthening PDPA training coverage`.
- One 4-row × 2-column table with grid borders.
- Evidence row shows two bulleted items.

Clean up: `rm /tmp/render_smoke.docx`.

- [ ] **Step 3: Commit**

```bash
git add src/render.py
git commit -m "feat(render): DOCX issue log with one 4-row table per issue"
```

---

## Task 16: `main.py` — wire the full pipeline

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Write the full CLI**

Replace `main.py` contents with:
```python
"""Operation Report Jedi — CLI entry point."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from src.config import load_config
from src.context import HELD_OUT_FILENAMES, build_context
from src.llm import make_client
from src.parsers import parse_folder, persist_parsed
from src.prompts.constraints import extract_constraints
from src.prompts.critique import critique_draft
from src.prompts.drafting import draft_issues
from src.render import render
from src.validate import build_validation
from src.versioning import next_version


def _log_line(fh: TextIO, stage: str, msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{stage:<12}] {msg}"
    fh.write(line + "\n")
    fh.flush()
    print(line)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Draft an Internal Audit issue log from a project folder.",
    )
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--issues", required=True, type=Path)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.project.is_dir():
        print(f"ERROR: --project {args.project} is not a directory", file=sys.stderr)
        return 1
    if not args.issues.is_file():
        print(f"ERROR: --issues {args.issues} is not a file", file=sys.stderr)
        return 1
    try:
        auditor_input = json.loads(args.issues.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {args.issues} is not valid JSON: {e}", file=sys.stderr)
        return 1

    cfg = load_config()
    client = make_client(cfg)

    version, run_dir = next_version(args.project)
    project_name = args.project.name.replace("_", " ").strip().title() \
        if args.project.name.islower() else args.project.name

    log_path = run_dir / "run.log"
    with log_path.open("w", encoding="utf-8") as log:
        _log_line(log, "start", f"project={args.project} version={version}")

        # Stage 1 — Parse
        print(f"[1/7] Parsing …")
        parsed = parse_folder(args.project, skip_filenames=HELD_OUT_FILENAMES)
        _log_line(log, "parse", f"parsed {len(parsed)} files")
        persist_parsed(parsed, run_dir)

        # Stage 2 — Build context
        print(f"[2/7] Building context …")
        ctx = build_context(parsed)
        total_chars = sum(len(v) for v in ctx.blobs.values())
        _log_line(log, "context",
                  f"assembled {total_chars:,} chars; FY2024 held out")
        for line in ctx.truncation_log:
            _log_line(log, "context", f"WARN: {line}")

        # Stage 3 — Extract constraints (LLM 1)
        print(f"[3/7] Extracting constraints …")
        c_res = extract_constraints(
            client, cfg.model,
            awp=ctx.blobs["AWP"], apm=ctx.blobs["APM"],
        )
        constraints = c_res.data
        (run_dir / "constraints.json").write_text(
            json.dumps(constraints, indent=2), encoding="utf-8"
        )
        _log_line(log, "step1",
                  f"OK. in={c_res.input_tokens} out={c_res.output_tokens} tokens")

        # Stage 4 — Draft issues (LLM 2)
        print(f"[4/7] Drafting issues …")
        d_res = draft_issues(
            client, cfg.model,
            constraints=constraints,
            guidelines=ctx.blobs["GUIDELINES"],
            samples=ctx.blobs["SAMPLES"],
            sop=ctx.blobs["SOP"],
            process_understanding=ctx.blobs["PROCESS_UNDERSTANDING"],
            auditor_input=auditor_input,
        )
        draft = d_res.data
        (run_dir / "draft.json").write_text(
            json.dumps(draft, indent=2), encoding="utf-8"
        )
        _log_line(log, "step2",
                  f"OK. in={d_res.input_tokens} out={d_res.output_tokens} tokens, "
                  f"{len(draft)} issues")

        # Stage 5 — Self-critique (LLM 3)
        print(f"[5/7] Self-critiquing …")
        cr_res = critique_draft(
            client, cfg.model,
            constraints=constraints,
            guidelines=ctx.blobs["GUIDELINES"],
            sop=ctx.blobs["SOP"],
            process_understanding=ctx.blobs["PROCESS_UNDERSTANDING"],
            draft=draft,
        )
        _log_line(log, "step3",
                  f"OK. in={cr_res.input_tokens} out={cr_res.output_tokens} tokens")

        # Stage 6 — Rule-based validate (+ merge)
        print(f"[6/7] Rule-based validation …")
        validation = build_validation(
            draft=draft,
            constraints=constraints,
            llm_critique=cr_res.data,
            context_truncated=ctx.truncated,
        )
        (run_dir / "validation.json").write_text(
            json.dumps(validation, indent=2), encoding="utf-8"
        )
        rb = validation["rule_based"]
        _log_line(log, "validate",
                  f"rule_based passed={rb['passed']} warnings={len(rb['warnings'])}")

        # Stage 7 — Render DOCX
        print(f"[7/7] Rendering DOCX …")
        docx_path = run_dir / f"{project_name}_Issue Log {version}.docx"
        render(draft, project_name=project_name, version=version, out_path=docx_path)
        _log_line(log, "render", f"wrote {docx_path}")

    print(f"\n→ {docx_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Walking-skeleton verify — full end-to-end run**

Run:
```bash
python main.py --project data/lumina_grand --issues sample_issues.json
```
Expected:
- Seven progress lines `[1/7] …` through `[7/7] …`.
- Final line `→ data/lumina_grand/Output/v0.1/Lumina Grand_Issue Log v0.1.docx`.
- Exit code 0.

Verify the run directory:
```bash
ls -la data/lumina_grand/Output/v0.1/
```
Expected files:
- `constraints.json`, `draft.json`, `validation.json`, `run.log`
- `Lumina Grand_Issue Log v0.1.docx`
- `parsed/` directory with 6 subfolders

- [ ] **Step 3: Verify re-run produces v0.2 without touching v0.1**

Run:
```bash
python main.py --project data/lumina_grand --issues sample_issues.json
ls data/lumina_grand/Output/
```
Expected: `v0.1  v0.2` (both directories present).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): wire all 7 pipeline stages end-to-end"
```

---

## Task 17: Polish — project_name derivation + output path cleanup

**Files:**
- Modify: `main.py`

The Task 16 code derives `project_name` with a hacky `.islower()` heuristic. Fix it properly.

- [ ] **Step 1: Replace the project_name derivation**

Find this block in `main.py` (roughly after `version, run_dir = next_version(...)`):
```python
    project_name = args.project.name.replace("_", " ").strip().title() \
        if args.project.name.islower() else args.project.name
```

Replace with:
```python
    # data/lumina_grand -> "Lumina Grand"
    project_name = args.project.name.replace("_", " ").replace("-", " ").strip()
    project_name = " ".join(w.capitalize() for w in project_name.split())
```

- [ ] **Step 2: Walking-skeleton verify**

Run:
```bash
python main.py --project data/lumina_grand --issues sample_issues.json
```
Expected: final line `→ data/lumina_grand/Output/v0.3/Lumina Grand_Issue Log v0.3.docx` (the project name part is exactly `Lumina Grand`).

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor(main): deterministic project-name derivation from folder"
```

---

## Task 18: Golden comparison + `POC_DEMO_NOTES.md`

**Files:**
- Create: `POC_DEMO_NOTES.md`

- [ ] **Step 1: Open the generated DOCX and the ground-truth PDF side-by-side**

Open:
- `data/lumina_grand/Output/v0.3/Lumina Grand_Issue Log v0.3.docx` (or whichever version is latest)
- `data/lumina_grand/Samples/FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf`

Eyeball comparison. For each generated issue, answer:
1. Does it map to a finding in the FY2024 PDF?
2. Is the tone comparable (positive-framed titles, constructive phrasing)?
3. Are the recommendations actionable?
4. Are there fabricated findings (not in the PDF, not in `sample_issues.json`)?

- [ ] **Step 2: Write `POC_DEMO_NOTES.md`**

Create `POC_DEMO_NOTES.md` with this structure, **filling in real observations from Step 1** (no placeholders, no "TBD"):

```markdown
# POC Demo Notes — Lumina Grand

**Run:** `data/lumina_grand/Output/v0.<N>/Lumina Grand_Issue Log v0.<N>.docx`
**Date:** <today>
**Auditor input:** <N> seeded issues from `sample_issues.json`

## What the POC does well

- <observation 1 — e.g., "Positive-framed titles per Guidelines (§2.1) — e.g., 'Strengthening PDPA training coverage'">
- <observation 2>
- <observation 3>

## Gaps vs. the approved FY2024 report

- <gap 1 — specific, e.g., "FY2024 report cites exact headcount figures; draft paraphrases evidence_summary without propagating the number">
- <gap 2>

## Validation surface

- **Rule-based warnings:** <count and a representative example, or "none">
- **LLM critique flags:** <count by severity, a representative flag>

## Which full-build modules would close each gap

| Gap | Full-build module |
|---|---|
| <gap 1> | <module, e.g., "Smart section selection (M4) — would surface the precise evidence passage instead of summary"> |
| <gap 2> | <module> |

## Ready-to-demo command

```bash
python main.py --project data/lumina_grand --issues sample_issues.json
```
```

- [ ] **Step 3: Commit**

```bash
git add POC_DEMO_NOTES.md
git commit -m "docs: POC demo notes with FY2024 golden comparison"
```

---

## Task 19: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Create `README.md`:
```markdown
# Operation Report Jedi — POC

AI-assisted drafting of Internal Audit issue logs for CDL. This POC runs on the Lumina Grand PDPA audit only.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows
# or: source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY, ANTHROPIC_MODEL (claude-sonnet-4-5), and ANTHROPIC_URI_ENDPOINT if applicable.
python test_connection.py          # smoke test the API
```

## Usage

```bash
python main.py --project data/lumina_grand --issues sample_issues.json
```

Each run lands in `data/lumina_grand/Output/v0.N/` with:
- `Lumina Grand_Issue Log v0.N.docx` — the draft
- `parsed/` — extracted Markdown of each artefact
- `constraints.json` — Step 1 scope envelope
- `draft.json` — Step 2 output (reviewed in the DOCX)
- `validation.json` — rule-based + LLM critique flags (informational)
- `run.log` — timestamped pipeline log

Re-runs bump `N`; prior versions are never overwritten.

## Inputs

- `--project` — a project folder containing six sub-folders: `APM/`, `AWP/`, `Guidelines/`, `Process SOP/`, `Process Understanding/`, `Samples/`, `Output/`.
- `--issues` — a JSON file; see `sample_issues.json` for the shape.

## Known limitations

- Single project only (Lumina Grand); no batch mode.
- No DOCX template fidelity — simple single-font tables.
- No cross-project evaluation framework.
- Always re-parses (no caching).
- Rule-based + LLM critique are informational; neither blocks output.

## Next steps

See `docs/WORK_BREAKDOWN_STRUCTURE.md` for the 45.5-day production roadmap.
The authoritative POC design is `docs/superpowers/specs/2026-04-18-end-to-end-poc-design.md`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, usage, and links"
```

---

## Self-Review Checklist

### Spec coverage

| Spec section | Implemented in task |
|---|---|
| §1–2 Summary & scope | Task 0 (bootstrap) + overall plan |
| §3.1 Procedural pipeline style | Task 1 (skeleton), Task 16 (wiring) |
| §3.2 Module layout | Task 1 (all modules created) |
| §3.3 Seven pipeline stages | Tasks 4–7 (parse), 8 (context), 10 (step 1), 12 (step 2), 13 (step 3), 14 (validate), 15 (render), 16 (wire) |
| §3.4 Run directory layout | Task 7 (persist_parsed) + Task 16 (writes all JSONs into run_dir) |
| §3.5 Held-out files | Task 8 (`HELD_OUT_FILENAMES`); Task 7 applies the skip |
| §4.1 `sample_issues.json` shape | Task 11 |
| §4.2 `constraints.json` schema | Task 10 prompt + Task 16 persistence |
| §4.3 `draft.json` schema | Task 12 prompt + Task 16 persistence |
| §4.4 `validation.json` schema | Task 13 (llm_critique) + Task 14 (merge) |
| §5.1 Step 1 prompt | Task 10 |
| §5.2 Step 2 prompt | Task 12 |
| §5.3 Step 3 prompt | Task 13 |
| §5.4 Cross-cutting (tokens, JSON fence, retry) | Task 3 (llm.py), Task 16 (token logging) |
| §6.1 Rule-based checks | Task 14 |
| §6.2 DOCX layout contract | Task 15 |
| §6.3 Versioning | Task 9 |
| §7.1 Error tiers | Task 3 (retry), Task 16 (setup errors) |
| §7.2 LLM retry specifics | Task 3 |
| §7.3 `run.log` | Task 16 |
| §7.4 Context budget & truncation | Task 8 |
| §8 CLI | Task 1 (skeleton), Task 16 (final) |
| §9 Testing strategy | Every task has a walking-skeleton verify step |
| §10 Success criteria | Task 16 (functional), Task 17 (filename), Task 18 (golden comparison) |
| §11 Hard rules preserved | 3-step chain (tasks 10/12/13), FY2024 hold-out (task 8), versioned dirs (task 9) |

### Placeholder scan
- No "TBD", "TODO", "implement later", "fill in details" strings anywhere.
- `sample_issues.json` template (Task 11) contains `<...>` angle-bracket prompts *inside a code block that is explicitly a template the engineer fills in from the FY2024 PDF* — not placeholder code. The task has an explicit step instructing the engineer to read the PDF and replace them.
- `POC_DEMO_NOTES.md` template (Task 18) similarly uses `<...>` markers the engineer fills in from manual comparison — this is the task's whole point.

### Type / name consistency
- `ParsedDoc` fields (`folder`, `filename`, `text`) — set in Task 4, used in Tasks 7, 8.
- `LLMResult` fields (`data`, `input_tokens`, `output_tokens`, `raw_text`) — set in Task 3, used in Tasks 10, 12, 13, 16.
- `ContextBlobs` fields (`blobs`, `truncated`, `truncation_log`) — set in Task 8, used in Task 16.
- `HELD_OUT_FILENAMES` — defined in Task 8, imported in Task 16.
- `next_version(project_path)` signature — Task 9, called in Task 16.
- `extract_constraints / draft_issues / critique_draft` signatures — Tasks 10/12/13, called in Task 16.
- `build_validation(draft, constraints, llm_critique, context_truncated)` — Task 14, called with matching kwargs in Task 16.
- `render(draft, project_name, version, out_path)` — Task 15, called positionally+by-name in Task 16.

All names match. No drift.
