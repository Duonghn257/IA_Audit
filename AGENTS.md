# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository nature

**Operation Report Jedi** — an AI-assisted audit-issue-log drafting POC for CDL Internal Audit. Current state:

- `docs/` — functional spec, architecture proposal, WBS, 5-day POC plan, and design specs from brainstorming sessions
- `data/lumina_grand/` — one complete sample audit project (PDPA audit; renamed from `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/`) used as the POC's only dataset
- `backend/requirements.txt` — Python dependencies for the POC
- `backend/test_connection.py` — Anthropic API smoke test (working)
- `backend/.env` / `backend/.env.example` — Anthropic and API configuration (`.env` override=True is intentional; see `backend/app/core/config.py`)
- `backend/app/` — modular backend: API, application services, domain, infrastructure and existing pipeline components
- `backend/api.py` — FastAPI ASGI entrypoint
- `backend/main.py` — compatibility CLI adapter; orchestration lives in `backend/app/application/audit_pipeline.py`
- `backend/sample_issues.json` — hand-seeded auditor input for Lumina Grand (2 entries derived from FY2024)
- `frontend/` — frontend module skeleton and design assets; Vue/Vite implementation is not initialized yet
- `POC_DEMO_NOTES.md` — golden comparison vs. the approved FY2024 report + gap→full-build-module mapping
- `README.md` — setup, usage, and links

**POC status: complete.** All 20 tasks (0–19) of `docs/superpowers/plans/2026-04-18-end-to-end-poc-implementation.md` are committed. Latest end-to-end run: `data/lumina_grand/Output/v0.3/` — produced with live Azure Anthropic calls on 2026-04-18.

## Source-of-truth documents (read in this order)

1. `docs/FUNCTIONAL_SPECIFICATION.md` — scope, inputs (6 artefact folders), outputs, success criteria. Everything derives from this.
2. `docs/superpowers/specs/2026-04-18-end-to-end-poc-design.md` — **the current authoritative spec** (produced by brainstorming 2026-04-18). Where this and the 5-day POC plan disagree, this spec wins.
3. `docs/POC_5DAY_IMPLEMENTATION_PLAN.md` — original 5-day plan; several decisions have been superseded (see below).
4. `docs/ARCHITECTURE_PROPOSAL_FINAL.md` — full 45.5-day production design. Long-term roadmap, not current target.
5. `docs/WORK_BREAKDOWN_STRUCTURE.md` (`.xlsx` mirror) — module/task breakdown for the full arch (M0–M8).
6. `_VI`-suffixed files are Vietnamese translations — secondary; do not update in tandem unless asked.

## Sample project layout (the 6-folder convention)

Every audit project has this structure; parsers key off folder name:

```
data/<project>/
  APM/                     # Approved Planning Memo — risk focus/intent
  AWP/                     # Approved Work Program — scope/objectives
  Guidelines/              # IA writing & formatting standards
  Process SOP/             # Approved process procedures (source of truth)
  Process Understanding/   # Process descriptions + evidence
  Samples/                 # Historical issue logs + issue log template
  Output/                  # Generated drafts land here; contains template.docx
```

On-disk sample: `data/lumina_grand/`. No spaces — safe to use unquoted.

## Confirmed POC design (2026-04-18 brainstorm)

These decisions supersede the 5-day plan where they differ.

1. **LLM provider**: Direct Anthropic API, model `claude-sonnet-4-5`. No Bedrock/AWS.
2. **Parsing**: Local libraries only — `python-docx`, `pdfplumber`, `openpyxl`.
3. **Project scope**: Lumina Grand only; no batch logic, no multi-project eval.
4. **Auditor input** (`backend/sample_issues.json`, hand-seeded): structured per-issue shape — `title_hint`, `observed_gap`, `evidence_summary`, `evidence_refs[]`, `sop_refs[]`, `risk_category` (optional).
5. **LLM chain**: **3-step** — (a) extract constraints from AWP+APM → `constraints.json`; (b) draft issues with full context + `<SCOPE>` + `<AUDITOR_INPUT>` → `draft.json`; (c) self-critique with flags `SCOPE_BREACH | UNSUPPORTED_ASSERTION | TONE_VIOLATION | WEAK_EVIDENCE` → `validation.json`.
6. **Samples strategy**: Hold out the approved FY2024 Lumina Grand PDF from context — only the past-audit issue-log reference (`1. Issue Log Template_version 11 Oct 2023.docx`, which is a populated issue log from an unrelated 2020 China sales audit repurposed as a house-style/format reference, not a blank template) feeds `<SAMPLES>`. FY2024 is reserved as ground truth for eyeball comparison.
7. **Output layout**: `data/<project>/Output/v0.N/` — DOCX + all intermediate artefacts nested per run.
8. **Entrypoints**: FastAPI via `uvicorn api:app --app-dir backend`; compatibility CLI via `python backend/main.py --project <path> --issues <json>`.
9. **Code organization**: Modular backend. API/CLI call `AuditPipeline`; existing parser/prompt/renderer functions live under `backend/app/pipeline/`.
10. **Validation semantics**: Rule-based checks + LLM self-critique both informational (non-blocking); surface in `validation.json` and `run.log`.

### Target module layout

```
ia_audit_report/
├── backend/
│   ├── main.py               # CLI entry, wires the 8 stages
│   ├── api.py                # FastAPI ASGI entry
│   ├── sample_issues.json    # hand-seeded auditor input (Lumina Grand)
│   └── app/
│       ├── api/
│       ├── application/
│       ├── bootstrap/
│       ├── core/
│       ├── domain/
│       ├── infrastructure/
│       └── pipeline/
├── frontend/
│   ├── design/
│   └── src/
├── docs/
└── data/
```

### Pipeline stages (per-run artefacts in `Output/v0.N/`)

1. **Parse** → `parsed/<folder>/<file>.md`
2. **Build context** → in-memory tagged blobs (`<AWP>`, `<APM>`, `<GUIDELINES>`, `<SAMPLES>`, `<SOP>`, `<PROCESS_UNDERSTANDING>`); FY2024 PDF held out
3. **Extract constraints** (LLM 1) → `constraints.json`
4. **Draft issues** (LLM 2) → `draft.json`
5. **Self-critique** (LLM 3) → `validation.json` (llm_critique section)
6. **Rule-based validate** → merges into `validation.json` (rule_based section); writes `run.log`
7. **Render** → `<Project>_Issue Log v0.N.docx`

## Environment

`backend/.env` / `backend/.env.example`: `ANTHROPIC_URI_ENDPOINT`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.
`.claude/settings.local.json` pre-permits `Bash(pip install *)`.

## Commands

Backend test harness uses pytest. CLI entry:

```bash
python backend/main.py --project data/lumina_grand --issues backend/sample_issues.json
```

API entry:

```bash
uvicorn api:app --app-dir backend --reload --port 8000
```

Tests:

```bash
pytest -q backend/tests
```

Smoke test: `python backend/test_connection.py` (verifies Azure Anthropic auth + model).

Dependencies (`backend/requirements.txt`): `anthropic`, `python-docx`, `pdfplumber`, `openpyxl`, `python-dotenv`.

## Conventions the code must honour

- **Output filename**: `<Project>_Issue Log v0.N.docx` inside `data/<project>/Output/v0.N/`. Re-runs bump N (scan Output/ for existing `v0.*` subfolders or DOCXes, pick `max+1`); **never overwrite an existing version**.
- **LLM context role tags**: `<AWP>`, `<APM>`, `<GUIDELINES>`, `<SAMPLES>`, `<SOP>`, `<PROCESS_UNDERSTANDING>`, `<SCOPE>` (from constraints.json), `<AUDITOR_INPUT>` (from `backend/sample_issues.json`), `<DRAFT>` (for critique step).
- **Scope guardrail**: prompts and validation must keep outputs inside `audit_scope` / `audited_entities` from `constraints.json`. The system is a drafting assistant; no content inferred beyond supplied artefacts (FUNCTIONAL_SPECIFICATION §5.2–5.3).
- **Intermediate artefacts**: `parsed/*.md`, `constraints.json`, `draft.json`, `validation.json`, `run.log` — all persisted beside the DOCX inside `Output/v0.N/`.
- **Held-out files**: `context.py` must exclude the FY2024 Lumina Grand PDF from `<SAMPLES>`. The `1. Issue Log Template_version 11 Oct 2023.docx` (populated past-audit issue log from a 2020 China sales project, repurposed as a style/format reference — not blank) remains included.

## What is deliberately out of scope for the POC

- AWS / Bedrock / S3 / IAM; Azure AI Document Intelligence or LlamaParse
- Smart TOC-based section selection; content-hash caching; parse caching
- DOCX template fidelity (matching fonts/styles from `Output/template.docx`)
- Multi-project batch runs, automated quality scoring
- `parse` / `generate` / `status` / `runs` subcommands
- Harvester / Sorter / Review Agent (post-POC per spec §10)

## Platform notes

- Running on Windows 11 under bash (Git Bash / WSL-style). Use **Unix shell syntax** (`/dev/null`, forward slashes); don't emit `NUL` or backslashes in commands.
- Windows cp1252 stdout cannot encode `…` or `→` — stick to ASCII in `print()` output (`backend/main.py` uses `...` and `->`).
- Primary working directory: `C:\Work\cdl\ia_audit_report` — a git repository; `main` is the working branch.
- Claude Code's runtime injects dummy `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` into the child shell; `backend/app/core/config.py` and `backend/test_connection.py` call `load_dotenv(override=True)` so the real `backend/.env` wins. Do not revert this.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ia_audit_report** (559 symbols, 656 relationships, 13 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/ia_audit_report/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ia_audit_report/clusters` | All functional areas |
| `gitnexus://repo/ia_audit_report/processes` | All execution flows |
| `gitnexus://repo/ia_audit_report/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
