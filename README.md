# Operation Report Jedi — POC

Operation Report Jedi is an AI-assisted workspace for drafting Internal Audit
issue logs for City Developments Limited (CDL). Auditors upload a project
folder, follow the processing stages in real time, and download the generated
DOCX issue log when the run completes.

The current proof of concept implements this workflow:

```text
Upload project folder
  → parse audit documents
  → build context and draft issues with an LLM
  → validate and render the report
  → download DOCX
```

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Nginx |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 in Docker; SQLite for zero-config local development |
| Processing | In-process background worker |
| LLM | Anthropic-compatible Messages API, including the company Azure endpoint |
| File storage | Persistent local filesystem volume for the POC |

## Repository layout

```text
.
├── backend/                # FastAPI API, pipeline, migrations, tests and CLI
│   ├── alembic/            # Database migrations
│   ├── app/                # Application source
│   ├── tests/              # Backend test suite
│   ├── .env.example        # Backend environment template
│   └── Dockerfile
├── frontend/               # Vue application and Nginx configuration
│   ├── design/             # Design references and original CDL logo
│   ├── src/                # Frontend source
│   └── Dockerfile
├── data/                   # Local audit fixtures used by the compatibility CLI
├── docs/                   # Product and architecture documentation
└── compose.yaml            # PostgreSQL, backend and frontend POC stack
```

## Recommended setup: Docker Compose

### 1. Prerequisites

Install the following software:

- Docker Engine or Docker Desktop.
- Docker Compose v2 (`docker compose`).
- Access to the company-provided Anthropic-compatible endpoint and API key.

No local Python, Node.js, PostgreSQL or Nginx installation is required for this
setup.

### 2. Configure the backend

From the repository root, create the backend environment file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and provide the LLM settings:

```dotenv
ANTHROPIC_URI_ENDPOINT=https://your-company-endpoint/anthropic/v1/messages
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_MODEL=your-model-name

API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
API_RUN_WORKERS=1
RAW_UPLOAD_RETENTION_DAYS=7
UPLOAD_MAX_FILES=500
UPLOAD_MAX_BYTES=1073741824
```

Do not commit `backend/.env` or expose its API key in logs, screenshots or issue
reports.

Compose provides these values inside the backend container automatically:

```text
DATABASE_URL=postgresql+psycopg://...@postgres:5432/audit_report
PROJECT_STORAGE_ROOT=/var/lib/ia-audit-report/projects
```

### 3. Optional Compose configuration

The stack has POC defaults and can run without a root `.env` file. To override
them, create `.env` in the repository root:

```dotenv
POSTGRES_DB=audit_report
POSTGRES_USER=audit_user
POSTGRES_PASSWORD=change-this-password
BACKEND_PORT=8010
FRONTEND_PORT=3010
```

Use URL-safe characters in `POSTGRES_PASSWORD` because Compose places the value
inside `DATABASE_URL`.

### 4. Build and start the stack

```bash
docker compose up --build -d
```

Compose performs the startup sequence automatically:

1. Start PostgreSQL and wait for its health check.
2. Run `alembic upgrade head` against PostgreSQL.
3. Start the FastAPI backend.
4. Build and serve the Vue frontend through Nginx.

Check the services:

```bash
docker compose ps
```

All three services should report `healthy`.

### 5. Open and verify the application

| Service | URL |
|---|---|
| Web application | `http://127.0.0.1:3010` |
| Backend API | `http://127.0.0.1:8010` |
| Swagger UI | `http://127.0.0.1:8010/docs` |
| OpenAPI document | `http://127.0.0.1:8010/openapi.json` |

Verify the API through the frontend reverse proxy:

```bash
curl http://127.0.0.1:3010/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "operation-report-jedi-backend",
  "version": "2.0.0"
}
```

Verify the active database migration:

```bash
docker compose exec backend alembic current
```

The current POC revision is:

```text
20260729_01 (head)
```

### 6. Upload a project

Open `http://127.0.0.1:3010`, select **New project**, and choose the complete
audit project folder.

The selected folder must contain `sample_issues.json` at its root:

```text
my-audit-project/
├── sample_issues.json       # Required by the current POC pipeline
├── APM/
├── AWP/
├── Guidelines/
├── Process SOP/
├── Process Understanding/
└── Samples/
```

The frontend preserves every file's relative path. After the upload, it shows
live progress using Server-Sent Events (SSE). A completed project provides a
**Download DOCX** action.

## Docker operations

View logs:

```bash
docker compose logs -f frontend backend postgres
```

Rebuild after source changes:

```bash
docker compose up --build -d
```

Restart one service:

```bash
docker compose restart backend
```

Stop the stack while preserving PostgreSQL and project files:

```bash
docker compose down
```

PostgreSQL data and uploaded/generated files are stored in separate named
volumes:

```text
operation-report-jedi_postgres_data
operation-report-jedi_project_storage
```

To inspect the database:

```bash
docker compose exec postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

> **Warning:** `docker compose down --volumes` permanently deletes the POC
> database and all project files stored in the Compose volumes.

## Local development

Docker Compose is the simplest way to run the complete application. Use the
following setup when developing the backend or frontend directly on the host.

### Backend

Requirements:

- Python 3.11 or newer.
- Access to the configured LLM endpoint.

Create the virtual environment and install dependencies:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
cp backend/.env.example backend/.env   # Skip if already configured
```

If `DATABASE_URL` is omitted, the backend uses SQLite at
`backend/.runtime/audit.db`. Apply the migrations and start the API:

```bash
cd backend
alembic upgrade head
cd ..

uvicorn api:app \
  --app-dir backend \
  --host 127.0.0.1 \
  --port 8010 \
  --reload
```

The API is now available at `http://127.0.0.1:8010`.

To use an external PostgreSQL database instead, set this value in
`backend/.env` before running Alembic:

```dotenv
DATABASE_URL=postgresql+psycopg://audit_user:password@127.0.0.1:5432/audit_report
```

### Frontend

Requirements:

- Node.js 22 or newer.
- npm.
- The backend running on port `8010`.

Install dependencies and start Vite:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api`
requests to `http://127.0.0.1:8010`.

## Database migrations

Run migration commands from `backend/` with the backend virtual environment
active:

```bash
cd backend
alembic current
alembic upgrade head
alembic check
```

Create a migration after changing a SQLAlchemy model:

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
alembic check
```

Review every autogenerated migration before applying it. The initial migration
assumes a new database. Do not run it directly against an existing schema that
was previously created with `Base.metadata.create_all()` without first
comparing the schemas and deciding whether `alembic stamp head` is appropriate.

## Tests and validation

Run the backend test suite:

```bash
source backend/.venv/bin/activate
pytest -q backend/tests
```

Run the frontend checks:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

Validate the Compose configuration and inspect the running stack:

```bash
docker compose config --quiet
docker compose ps
curl --fail http://127.0.0.1:3010/api/v1/health
```

Default automated tests do not call the live LLM endpoint.

## Compatibility CLI

The original pipeline can still be run without the web application:

```bash
source backend/.venv/bin/activate
python backend/main.py \
  --project data/lumina_grand \
  --issues backend/sample_issues.json
```

Generated files are written under:

```text
data/lumina_grand/Output/v0.N/
```

Each new run increments the version and keeps earlier outputs.

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_URI_ENDPOINT` | Required | Anthropic-compatible Messages API endpoint |
| `ANTHROPIC_API_KEY` | Required | LLM credential |
| `ANTHROPIC_MODEL` | Required | Model identifier accepted by the endpoint |
| `DATABASE_URL` | SQLite locally | SQLAlchemy database URL |
| `PROJECT_STORAGE_ROOT` | `backend/.runtime/projects` locally | Raw upload and generated output storage |
| `RAW_UPLOAD_RETENTION_DAYS` | `7` | Number of days to retain raw input |
| `UPLOAD_MAX_FILES` | `500` | Maximum files in one folder upload |
| `UPLOAD_MAX_BYTES` | `1073741824` | Maximum total upload size in bytes |
| `API_CORS_ORIGINS` | Local Vite origins | Comma-separated allowed frontend origins |
| `API_RUN_WORKERS` | `1` | Number of in-process background threads |
| `BACKEND_PORT` | `8010` | Backend host port used by Compose |
| `FRONTEND_PORT` | `3010` | Frontend host port used by Compose |
| `POSTGRES_DB` | `audit_report` | Compose PostgreSQL database name |
| `POSTGRES_USER` | `audit_user` | Compose PostgreSQL user |
| `POSTGRES_PASSWORD` | POC-only default | Compose PostgreSQL password |

## Troubleshooting

### A service is not healthy

```bash
docker compose ps
docker compose logs --tail=200 backend postgres frontend
```

### Port 3010 or 8010 is already in use

Set different host ports in the root `.env`, then recreate the stack:

```dotenv
FRONTEND_PORT=3011
BACKEND_PORT=8011
```

```bash
docker compose up -d
```

### Upload fails immediately

Check that:

- `sample_issues.json` exists at the selected folder root.
- The folder contains no more than `UPLOAD_MAX_FILES` files.
- The total size does not exceed `UPLOAD_MAX_BYTES`.
- Nginx, the backend and PostgreSQL are healthy.

### A project remains in `PROCESSING` after a restart

The POC uses an in-process background thread and does not yet provide durable
job recovery. Upload the folder as a new project.

### Swagger displays uploaded files as strange text

The API accepts multipart files correctly, but some Swagger UI/OpenAPI 3.1
combinations render arrays of uploaded files as text fields. Use the web
application at `http://127.0.0.1:3010` or a multipart-aware HTTP client for
folder uploads.

## POC limitations

- The project folder must include `sample_issues.json` at its root.
- Background execution runs inside the API process.
- Restart recovery, retry and cancellation are not implemented.
- Storage uses a local Docker volume rather than object storage.
- Authentication and project ownership are not implemented.
- Raw-input cleanup runs when the backend starts, not on a scheduler.
- The legacy `/api/v1/runs` API still uses in-memory state.

## Additional documentation

- [Backend API and storage details](backend/README.md)
- [Frontend development guide](frontend/README.md)
- [Frontend POC flow](docs/v2/FRONTEND_FLOW.md)
- [Implementation handoff](docs/v2/IMPLEMENTATION_HANDOFF.md)
- [Source architecture](docs/v2/SOURCE_CODE_ARCHITECTURE.md)
