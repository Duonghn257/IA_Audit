# Trạng thái Infrastructure

> Xác minh gần nhất: 03/08/2026
> Trạng thái bàn giao: POC stack đang hoạt động
> Source of truth: `compose.yaml`, Dockerfiles và `frontend/nginx.conf`

## Kết quả hiện tại

POC chạy trên một Docker Compose stack, có PostgreSQL và project-storage volumes
riêng để giữ dữ liệu.

```text
Browser :3010
  → frontend (Nginx :8080)
      → /api/* proxy
          → backend (FastAPI :8000, host :8010)
              → PostgreSQL :5432
              → project_storage volume
```

## Service inventory

| Service | Image/build | Host access | Health dependency |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | Internal only | `pg_isready` |
| `backend` | `backend/Dockerfile` | `127.0.0.1:8010` mặc định | Chờ PostgreSQL healthy |
| `frontend` | `frontend/Dockerfile` | `127.0.0.1:3010` mặc định | Chờ backend healthy |

Thứ tự startup:

1. PostgreSQL start và pass health check.
2. Backend chạy `alembic upgrade head`.
3. Uvicorn start FastAPI app.
4. Nginx phục vụ Vue build và proxy `/api/`.

## Persistence

| Dữ liệu | Storage | Lifecycle |
|---|---|---|
| PostgreSQL data | Named volume `postgres_data` | Được giữ khi chạy `docker compose down` |
| Uploaded folders và outputs | Named volume `project_storage` | Được giữ khi chạy `docker compose down` |
| Project/event metadata | PostgreSQL | Durable qua container restart |
| Raw input | Project storage | Retention mặc định 7 ngày |
| Generated DOCX | Project storage | Tách khỏi raw-input cleanup |

Không chạy `docker compose down --volumes` nếu cần giữ database hoặc project
files.

## Database migration

```text
backend/alembic/versions/20260729_01_create_projects.py
revision: 20260729_01
status: head
```

Compose tự apply migration trước khi start Uvicorn. Các lệnh thường dùng:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic check
docker compose exec backend alembic upgrade head
```

## Nginx behavior

Frontend server hiện có:

- SPA fallback về `index.html`.
- `/api/` reverse proxy sang backend service.
- Tắt proxy buffering cho SSE.
- Proxy read/send timeout một giờ.
- Request body tối đa 1 GB.
- Cache static assets bảy ngày.

## Configuration

LLM credentials đặt trong `backend/.env`:

```dotenv
ANTHROPIC_URI_ENDPOINT=...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=...
```

Root `.env` có thể override:

```dotenv
POSTGRES_DB=audit_report
POSTGRES_USER=audit_user
POSTGRES_PASSWORD=change-this-password
BACKEND_PORT=8010
FRONTEND_PORT=3010
```

Compose inject `DATABASE_URL` và `PROJECT_STORAGE_ROOT` vào backend. Không commit
secrets hoặc đưa secrets vào logs/screenshots.

## Baseline kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| `docker compose config --quiet` | Pass |
| PostgreSQL container | Healthy |
| Backend container | Healthy |
| Frontend container | Healthy |
| `GET :3010/api/v1/health` | HTTP 200 |
| `GET :3010/api/v1/projects` | HTTP 200 |
| Alembic current | `20260729_01 (head)` |
| Alembic check | Không có schema drift |
| Nginx config và SPA fallback | Pass |
| API/SSE reverse proxy | Pass |

Quick verification:

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:3010/api/v1/health
docker compose exec backend alembic current
```

## Giới hạn trước production

- Default Compose database credentials chỉ dùng cho POC.
- Chưa có TLS termination hoặc public routing config.
- Chưa có secrets manager hoặc workload identity.
- Chưa có backup/restore procedure cho PostgreSQL và project files.
- Chưa có encrypted object storage, antivirus scanning hoặc retention scheduler.
- Chưa có centralized logs, metrics, traces hoặc alerts.
- Chưa có durable worker, retry queue hoặc dead-letter queue.
- Single-host Compose không phải production topology.

## Khi nào cập nhật file này

Cập nhật khi Compose services, ports, migrations, volumes, proxy rules,
environment variables hoặc operational checks thay đổi. Production improvements
nằm tại [roadmap](../roadmap/README.md).
