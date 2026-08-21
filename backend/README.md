# Backend

Backend is a modular FastAPI application with persistent project status,
folder upload, background processing, progress events and DOCX download.
The compatibility CLI is still available.

## Structure

```text
backend/
├── api.py                         # ASGI entrypoint
├── main.py                        # Compatibility CLI adapter
├── app/
│   ├── api/                       # HTTP routes, schemas, errors, middleware
│   ├── ai/                        # Anthropic client, prompts, AI validation
│   ├── application/               # Workflow orchestration, managers, ports
│   ├── bootstrap/                 # FastAPI composition root
│   ├── core/                      # LLM/API settings
│   ├── documents/                 # Parsers, template inspection, DOCX rendering
│   ├── domain/                    # Project/run states and events
│   ├── infrastructure/            # SQL repository, storage, run store
│   └── rag/                       # Retrieval and context assembly boundary
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

Dependency direction:

```text
API / CLI → Application → Domain
                     ↘ Infrastructure adapters
Application workflow → AI + RAG + Documents
```

`main.py`, the legacy run API and project upload workflow call the same
`AuditPipeline`; orchestration is not duplicated in HTTP routes.

The AI and RAG code lives inside `backend/app` and shares the backend domain,
repository and schema boundaries. It is not a separate service or repository.
Future API and worker processes may use the same package and container image.

## POC workflow

```text
Folder upload
  → UPLOADING
  → PROCESSING
  → COMPLETED | FAILED
  → download DOCX when COMPLETED
```

`COMPLETED` is only written after the DOCX has been rendered and copied from
raw `input/` staging to durable `output/` storage. There are no Observation or
Draft Review API gates in the current POC.

## Setup

Run from the repository root:

```bash
source backend/.venv/bin/activate
pip install -r backend/requirements-dev.txt
cp backend/.env.example backend/.env
```

## Run the API

```bash
uvicorn api:app \
  --app-dir backend \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

Useful URLs:

- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

Upload a project folder:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/upload \
  -F 'name=CDL Hospitality Trusts Audit FY2024' \
  -F 'files=@backend/sample_issues.json' \
  -F 'relative_paths=CDL Audit/sample_issues.json' \
  -F 'files=@data/lumina_grand/APM/Approved Planning Memo.docx' \
  -F 'relative_paths=CDL Audit/APM/Approved Planning Memo.docx'
```

The browser must repeat `files` and `relative_paths` in the same order for
every selected file. A POC folder must contain `sample_issues.json` at its
root.

Project endpoints:

```text
POST /api/v1/projects/upload
GET  /api/v1/projects
GET  /api/v1/projects/{project_id}
GET  /api/v1/projects/{project_id}/events
GET  /api/v1/projects/{project_id}/events/stream
GET  /api/v1/projects/{project_id}/output
GET  /api/v1/health
```

The SSE endpoint emits pipeline progress suitable for the frontend thinking
view. The old `/api/v1/runs` endpoints remain temporarily for compatibility;
their state is still in memory.

## Database and storage

Project metadata and progress events are stored through SQLAlchemy:

```dotenv
DATABASE_URL=postgresql+psycopg://audit_user:password@localhost:5432/audit_report
```

If `DATABASE_URL` is omitted, local development uses
`backend/.runtime/audit.db`. Tables are auto-created for the POC.

Do not store uploaded documents or DOCX binaries in PostgreSQL:

```text
PROJECT_STORAGE_ROOT/
└── {project_id}/
    ├── input/     # raw uploaded folder and pipeline working files
    └── output/    # promoted DOCX, independent from raw cleanup
```

Raw `input/` is retained for seven days by default. Expired terminal projects
are cleaned on application startup; output and database metadata remain.

```dotenv
PROJECT_STORAGE_ROOT=/secure/project-storage
RAW_UPLOAD_RETENTION_DAYS=7
UPLOAD_MAX_FILES=500
UPLOAD_MAX_BYTES=1073741824
```

For production, use encrypted S3/object storage, scheduled lifecycle cleanup,
Alembic migrations and a durable job queue. These replace infrastructure
adapters without changing the project API or application workflow.

## CLI compatibility

```bash
python backend/main.py \
  --project data/lumina_grand \
  --issues backend/sample_issues.json
```

## Docker Compose POC

The POC stack runs a dedicated PostgreSQL 16 database and the FastAPI backend.
Alembic migrations run automatically before Uvicorn starts. The default host port
is `8010` because port `8000` may already be in use on a shared VPS.

```bash
cp backend/.env.example backend/.env  # skip if already configured
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8010/api/v1/health
docker compose exec backend alembic current
```

PostgreSQL data and uploaded/generated project files use separate named volumes.
`docker compose down` preserves both volumes. Do not add `--volumes` unless the
POC database and stored project files should be deleted.

Override the POC defaults through a root `.env` or exported variables:

```dotenv
POSTGRES_DB=audit_report
POSTGRES_USER=audit_user
POSTGRES_PASSWORD=change-me
BACKEND_PORT=8010
FRONTEND_PORT=3010
```

For local, non-Docker migration commands, activate the virtualenv first:

```bash
cd backend
alembic upgrade head
alembic current
alembic check
```

The initial migration assumes a new database. For a pre-existing database that
was created with SQLAlchemy `create_all`, verify that its schema matches before
using `alembic stamp head`.

## Test

```bash
pytest -q backend/tests
```

Default tests never call the live LLM. They cover repository persistence,
folder/path safety, upload-to-terminal workflow, failure status and DOCX
download.
