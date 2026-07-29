# Frontend

Vue 3 + Vite frontend for the Operation Report Jedi POC. It implements the
single Projects workflow defined in `docs/v2/FRONTEND_FLOW.md`:

```text
Select folder → upload → live SSE progress → completed/failed → download DOCX
```

## Run with the full POC stack

From the repository root:

```bash
docker compose up --build -d
# Open http://127.0.0.1:3010 in your browser
```

Nginx serves the production build and proxies `/api/*` to the backend service.
The backend remains directly available on `http://127.0.0.1:8010`.

## Local development

Node 22 or newer is recommended:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app on `http://127.0.0.1:5173` and proxies API calls to the
Docker backend on port `8010`.

## Validation

```bash
npm run typecheck
npm run test
npm run build
```

The folder picker requires `sample_issues.json` at the selected folder root,
matching the current backend POC contract.
