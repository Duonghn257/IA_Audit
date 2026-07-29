# Operation Report Jedi — POC

AI-assisted drafting of Internal Audit issue logs for CDL. This POC runs on the Lumina Grand PDPA audit only.

## Repository layout

```text
ia_audit_report/
├── backend/          # FastAPI, pipeline, persistence, storage and CLI
├── frontend/         # Frontend source structure and design assets
├── docs/             # Product, architecture and implementation documents
└── data/             # Local audit project fixtures and generated outputs
```

## Setup

```bash
python -m venv backend/.venv
source backend/.venv/Scripts/activate      # Git Bash on Windows
# or: source backend/.venv/bin/activate    # Linux/macOS
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env: set ANTHROPIC_API_KEY, ANTHROPIC_MODEL (claude-sonnet-4-5), and ANTHROPIC_URI_ENDPOINT if applicable.
python backend/test_connection.py          # smoke test the API
```

## Docker POC quick start

```bash
docker compose up --build -d
# Open http://127.0.0.1:3010 in your browser
curl http://127.0.0.1:3010/api/v1/health
```

This starts PostgreSQL 16, applies Alembic migrations, starts the FastAPI backend,
and serves the Vue frontend through Nginx on port `3010`. Data is retained in named Docker volumes. See
[`backend/README.md`](backend/README.md) for configuration and operations.

## Usage

### API

```bash
uvicorn api:app --app-dir backend --reload --port 8000
```

Swagger UI is available at `http://127.0.0.1:8000/docs`.

Current frontend integration flow:

```text
POST folder to /api/v1/projects/upload
  → GET project status or subscribe to SSE progress
  → COMPLETED / FAILED
  → download DOCX from /api/v1/projects/{id}/output
```

See [`backend/README.md`](backend/README.md) for the multipart contract,
PostgreSQL configuration and storage retention policy.

### CLI

```bash
python backend/main.py \
  --project data/lumina_grand \
  --issues backend/sample_issues.json
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
- `--issues` — a JSON file; see `backend/sample_issues.json` for the shape.

## Known limitations

- Folder upload currently requires `sample_issues.json` at project root.
- Project execution uses an in-process thread; use a durable queue for
  multi-instance production.
- Local storage is the POC adapter; production should use encrypted object
  storage and SharePoint integration.
- No DOCX template fidelity — simple single-font tables.
- No cross-project evaluation framework.
- Always re-parses (no caching).
- Rule-based + LLM critique are informational; neither blocks output.

## Next steps

See `docs/WORK_BREAKDOWN_STRUCTURE.md` for the 45.5-day production roadmap.
The authoritative POC design is `docs/superpowers/specs/2026-04-18-end-to-end-poc-design.md`.
