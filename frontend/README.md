# Frontend

Vue 3 + Vite frontend for the Operation Report Jedi POC. It implements the
single Projects workflow defined in `docs/v2/status/FRONTEND.md`:

```text
Project & artefacts → enter/import auditor inputs → review → upload
  → live SSE progress → completed/failed → download DOCX
```

## Run with the full POC stack

From the repository root:

```bash
docker compose --env-file frontend/.env up --build -d
# Open http://127.0.0.1:3010 in your browser
```

Nginx serves the production build and proxies `/api/*` to the backend service.
The backend remains directly available on `http://127.0.0.1:8010`.

## Local development

Node 22 or newer is recommended:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite serves the app on `http://127.0.0.1:5173` and proxies API calls to the
Docker backend on port `8010`.

`VITE_API_BASE_URL` controls the backend origin used by all requests in
`src/shared/api/projects.ts`. Set only the origin, for example
`http://10.22.14.6:3000/`; the API client appends `/api/v1` automatically. If
the variable is empty, requests use the same origin as the frontend. Restart
the Vite development server after changing `.env`.

## Validation

```bash
npm run typecheck
npm run test
npm run build
```

`sample_issues.json` is no longer required in the selected folder. The setup
wizard accepts manual auditor input or JSON import, then generates the root file
for the existing backend POC contract after the user reviews the issues.

Reference selectors mirror the backend parser and show only direct `.docx`,
`.pdf`, and `.xlsx` files from `APM`, `AWP`, `Guidelines`, `Process SOP`,
`Process Understanding`, and `Samples`. Hidden files such as `.DS_Store`,
temporary Word files, `Output/**`, nested generated files, and unsupported
extensions are excluded from the selectors. This UI filter does not delete or
remove files from the original folder upload.
