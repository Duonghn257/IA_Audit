# Operation Report Jedi — Implementation Handoff

> **Ngày cập nhật:** 29/07/2026
>
> **Mục đích:** Giữ đầy đủ context để tiếp tục phát triển trên VPS
>
> **Trạng thái:** Backend POC đã có API, persistence, upload, progress và DOCX download; frontend chưa được khởi tạo thành ứng dụng Vue/Vite

## 1. Đọc gì trước khi tiếp tục

Thứ tự đọc đề xuất:

1. File này — trạng thái thực tế và checklist chuyển VPS.
2. [Frontend Flow](FRONTEND_FLOW.md) — flow POC đã chốt.
3. [Source Code Architecture](SOURCE_CODE_ARCHITECTURE.md) — kiến trúc source và hướng mở rộng.
4. [Architecture v2](README.md) — target dài hạn sau POC.
5. [`backend/README.md`](../../backend/README.md) — hướng dẫn chạy backend và API.

Khi nội dung mâu thuẫn, ưu tiên theo thứ tự:

```text
IMPLEMENTATION_HANDOFF.md
  → FRONTEND_FLOW.md
  → code hiện tại
  → SOURCE_CODE_ARCHITECTURE.md
  → target dài hạn trong README.md
```

## 2. Scope POC đã chốt

Frontend và backend hiện chỉ cần flow:

```text
Auditor chọn local project folder
  → backend nhận và lưu folder
  → pipeline xử lý nền
  → frontend hiển thị live progress
  → project thành COMPLETED hoặc FAILED
  → nếu COMPLETED thì tải DOCX
```

Không làm trong POC hiện tại:

- Observation Inbox.
- Add/Edit/Merge/Reject observation.
- Draft Issue Review.
- Approval gate trước export.
- SharePoint folder picker.
- Publish DOCX ngược lên SharePoint.

Khi production, local upload sẽ được thay bằng SharePoint adapter. Project
status, progress event và output contract nên giữ nguyên.

## 3. Các quyết định kiến trúc quan trọng

### 3.1 Trạng thái project

Project chỉ có bốn trạng thái:

```text
UPLOADING → PROCESSING → COMPLETED
     │            │
     └────────────┴────────→ FAILED
```

- `UPLOADING`: backend đang nhận/lưu folder.
- `PROCESSING`: pipeline đang parse, gọi LLM, validate và render.
- `COMPLETED`: DOCX đã render và đã được copy sang output storage.
- `FAILED`: upload hoặc bất kỳ stage nào bị lỗi.

Các stage như `PARSING`, `CONTEXT`, `DRAFTING`, `VALIDATING`,
`RENDERING` là progress event, không phải project status.

### 3.2 Database và file storage

PostgreSQL chỉ lưu dữ liệu cần cho project list/status:

- Project ID, name và source type.
- Status/current activity/error.
- Created/updated/started/completed timestamps.
- Version và issue count.
- Raw input expiry/deleted timestamps.
- Internal storage/output references.
- Progress event log.

Không lưu uploaded documents hoặc DOCX binary trong PostgreSQL.

File layout POC:

```text
PROJECT_STORAGE_ROOT/
└── {project_id}/
    ├── input/     # raw uploaded folder + working artefacts của pipeline
    └── output/    # DOCX đã promote sau khi render thành công
```

Raw `input/` giữ 7 ngày mặc định để debug/retry. Sau thời hạn này input được
xóa, còn:

- `output/` vẫn giữ DOCX.
- PostgreSQL vẫn giữ metadata/status/events.

Cleanup hiện chạy khi application startup. Production nên có scheduled worker
hoặc object-storage lifecycle để cleanup đúng thời điểm.

### 3.3 Ports and adapters

Application workflow phụ thuộc protocol trong
`backend/app/application/ports.py`, không phụ thuộc trực tiếp PostgreSQL,
SharePoint hoặc S3.

Adapter hiện tại:

| Port/capability | POC adapter | Production target |
|---|---|---|
| Project repository | SQLAlchemy | PostgreSQL qua SQLAlchemy |
| Project storage | Local filesystem | Encrypted S3/object storage |
| Background execution | `ThreadPoolExecutor` | SQS/Celery/worker |
| Project source | Browser folder upload | Microsoft Graph/SharePoint |
| LLM | Anthropic-compatible endpoint | Anthropic hoặc Bedrock adapter |

## 4. Những gì đã triển khai

### 4.1 Repository đã được tổ chức lại

```text
ia_audit_report/
├── backend/
│   ├── .venv/                  # virtualenv local macOS
│   ├── api.py                  # ASGI entrypoint
│   ├── main.py                 # CLI compatibility
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── design/                 # design references đã được move vào đây
│   ├── src/                    # module boundaries, chưa có Vue app
│   └── tests/
└── docs/
    └── v2/
```

Source Python cũ từ root `src/` đã được chuyển vào
`backend/app/pipeline/`. Các entrypoint/config/dependency liên quan đã chuyển
vào `backend/`.

### 4.2 Backend layers

```text
backend/app/
├── api/
│   ├── routes/                 # health, projects, legacy runs
│   ├── schemas/                # response/request schemas
│   ├── dependencies.py
│   ├── errors.py
│   ├── middleware.py
│   └── router.py
├── application/
│   ├── audit_pipeline.py       # orchestration pipeline hiện tại
│   ├── project_manager.py      # upload/process/retention use case
│   ├── project_files.py
│   ├── ports.py
│   ├── path_resolver.py
│   └── run_manager.py          # legacy compatibility
├── bootstrap/
│   └── api.py                  # composition root
├── core/
│   ├── config.py               # LLM configuration
│   └── settings.py             # API/database/storage settings
├── domain/
│   ├── projects.py
│   └── runs.py
├── infrastructure/
│   ├── database.py
│   ├── project_repository.py
│   ├── project_storage.py
│   └── run_store.py
└── pipeline/
    ├── parsers.py
    ├── context.py
    ├── llm.py
    ├── prompts/
    ├── validate.py
    ├── render.py
    └── versioning.py
```

Dependency direction:

```text
API → Application → Domain
          ↓
        Ports
          ↑
Infrastructure adapters
```

FastAPI route không chứa pipeline logic. `ProjectManager` gọi
`AuditPipeline`; CLI và legacy `/runs` cũng dùng cùng pipeline.

### 4.3 Project workflow

`ProjectManager.submit_upload()` thực hiện:

1. Tạo UUID và project record `UPLOADING`.
2. Stream từng file xuống storage, không dùng absolute path từ máy auditor.
3. Validate relative path, file count và tổng dung lượng.
4. Ghi upload progress event.
5. Chuyển project sang `PROCESSING`.
6. Submit background task.
7. Pipeline emit progress event vào database.
8. Render DOCX vào working folder.
9. Copy DOCX sang `{project_id}/output/`.
10. Chỉ sau bước 9 mới chuyển sang `COMPLETED`.
11. Nếu bất kỳ bước nào lỗi, ghi error và chuyển sang `FAILED`.

### 4.4 Pipeline hiện tại

Pipeline vẫn là tám stage:

```text
1. PARSING       Parse project documents
2. CONTEXT       Build audit context
3. CONSTRAINTS   Extract scope and constraints
4. DRAFTING      Draft audit issues
5. CRITIQUING    Review draft quality
6. STYLING       Produce DOCX style specification
7. VALIDATING    Validate generated issues
8. RENDERING     Generate DOCX
```

Frontend chỉ hiển thị stage/activity; user không dừng lại để review draft.

Giới hạn quan trọng: folder upload hiện phải có `sample_issues.json` ở root.
Pipeline vẫn dùng file này làm auditor input. Nếu thiếu, background job chuyển
project sang `FAILED` với message:

```text
Missing sample_issues.json at the root of the uploaded project folder.
```

Không được âm thầm dùng `backend/sample_issues.json` cho mọi project vì có thể
trộn dữ liệu audit giữa các project.

## 5. API contract cho frontend

### 5.1 Endpoints

```text
GET  /api/v1/health

POST /api/v1/projects/upload
GET  /api/v1/projects
GET  /api/v1/projects/{project_id}
GET  /api/v1/projects/{project_id}/events
GET  /api/v1/projects/{project_id}/events/stream
GET  /api/v1/projects/{project_id}/output
```

Legacy endpoints vẫn còn để tương thích:

```text
POST /api/v1/runs
GET  /api/v1/runs
GET  /api/v1/runs/{run_id}
GET  /api/v1/runs/{run_id}/events
GET  /api/v1/runs/{run_id}/events/stream
GET  /api/v1/runs/{run_id}/output
```

Legacy `/runs` dùng in-memory store và không phải contract chính cho frontend
mới.

### 5.2 Folder upload

Request là `multipart/form-data`:

| Field | Kiểu | Ghi chú |
|---|---|---|
| `name` | string, optional | Tên project |
| `files` | repeated file | Content của từng file |
| `relative_paths` | repeated string | Phải cùng số lượng và thứ tự với `files` |

Frontend browser:

```ts
const form = new FormData();
form.append("name", projectName);

for (const file of selectedFiles) {
  form.append("files", file);
  form.append("relative_paths", file.webkitRelativePath);
}

const response = await fetch("/api/v1/projects/upload", {
  method: "POST",
  body: form,
});
```

Input element:

```html
<input type="file" webkitdirectory multiple />
```

Backend bỏ common selected-folder prefix trước khi lưu. Ví dụ:

```text
CDL Audit/APM/apm.docx
CDL Audit/sample_issues.json
```

được lưu thành:

```text
input/APM/apm.docx
input/sample_issues.json
```

### 5.3 Project response

Response không expose `storage_path` hoặc absolute server path:

```json
{
  "project_id": "opaque-uuid",
  "name": "CDL Hospitality Trusts Audit FY2024",
  "source_type": "FILE_UPLOAD",
  "status": "PROCESSING",
  "current_activity": "Parsing project documents...",
  "allowed_actions": [
    "VIEW_STATUS",
    "VIEW_PROGRESS"
  ],
  "created_at": "2026-07-29T06:00:00Z",
  "updated_at": "2026-07-29T06:00:05Z",
  "started_at": "2026-07-29T06:00:05Z",
  "completed_at": null,
  "output_available": false,
  "output_download_url": null,
  "version": null,
  "issue_count": null,
  "error": null,
  "raw_expires_at": "2026-08-05T06:00:00Z",
  "raw_deleted_at": null
}
```

Frontend phải dùng `allowed_actions`:

| Action | UI behavior |
|---|---|
| `VIEW_STATUS` | Cho mở project detail |
| `VIEW_PROGRESS` | Hiển thị activity timeline |
| `DOWNLOAD_OUTPUT` | Enable Download DOCX |

### 5.4 Progress

Polling:

```text
GET /api/v1/projects/{project_id}/events?after_event_id={last_id}
```

SSE:

```text
GET /api/v1/projects/{project_id}/events/stream?after_event_id={last_id}
```

SSE emit:

- `event: progress` cho từng progress event.
- `event: end` khi project terminal và không còn event mới.
- Heartbeat comment khi idle.

Sau `end`, frontend nên gọi lại project detail endpoint để lấy snapshot cuối.

### 5.5 Stable errors

API errors có contract:

```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "Project not found: ...",
    "details": {},
    "correlation_id": "..."
  }
}
```

Các code chính:

| Code | HTTP | Ý nghĩa |
|---|---:|---|
| `INVALID_FOLDER_UPLOAD` | 422 | Relative path/files không hợp lệ |
| `INVALID_PROJECT_NAME` | 422 | Project name rỗng |
| `PROJECT_NOT_FOUND` | 404 | Không có project |
| `OUTPUT_NOT_READY` | 409 | Project chưa completed |
| `OUTPUT_NOT_FOUND` | 410 | Metadata có nhưng file output không còn |

## 6. Database schema hiện tại

SQLAlchemy auto-create hai table trong POC.

### `projects`

Các cột chính:

```text
project_id                 UUID string primary key
name
source_type                FILE_UPLOAD
status
current_activity
created_at
updated_at
started_at
completed_at
storage_path               internal only
output_path                internal only
version
issue_count
error
raw_expires_at
raw_deleted_at
```

### `project_events`

```text
event_id                   auto-increment sequence
project_id                 foreign key
stage
message
completed_steps
total_steps
warning
occurred_at
```

SQLite được dùng làm zero-config local default. PostgreSQL dùng cùng
repository:

```dotenv
DATABASE_URL=postgresql+psycopg://audit_user:password@localhost:5432/audit_report
```

POC đang dùng `Base.metadata.create_all()`. Trước production/multi-instance,
cần thêm Alembic và migration history.

## 7. Configuration

File mẫu: `backend/.env.example`.

| Variable | Default/required | Mục đích |
|---|---|---|
| `ANTHROPIC_URI_ENDPOINT` | Required để chạy pipeline thật | LLM messages endpoint |
| `ANTHROPIC_API_KEY` | Required để chạy pipeline thật | LLM credential |
| `ANTHROPIC_MODEL` | Required | Model name |
| `DATABASE_URL` | SQLite local | PostgreSQL connection URL |
| `PROJECT_STORAGE_ROOT` | `backend/.runtime/projects` | Raw/output storage |
| `RAW_UPLOAD_RETENTION_DAYS` | `7` | Thời gian giữ raw input |
| `UPLOAD_MAX_FILES` | `500` | Giới hạn file/folder |
| `UPLOAD_MAX_BYTES` | `1073741824` | Tổng upload limit, mặc định 1 GiB |
| `API_CORS_ORIGINS` | localhost Vite origins | Allowed frontend origins |
| `API_RUN_WORKERS` | `1` | Số background threads |
| `API_DATA_ROOT` | repository `data/` | Chỉ dùng legacy `/runs` path validation |

Không commit `.env` hoặc API key.

## 8. Tests và verification đã chạy

Command:

```bash
backend/.venv/bin/pytest -q backend/tests
```

Kết quả gần nhất:

```text
12 passed, 1 warning
```

Warning duy nhất là Starlette deprecation liên quan `TestClient/httpx`, không
phải lỗi application.

Test coverage hiện có:

- Legacy health/run API contract.
- Invalid legacy path.
- Stable API error.
- Audit pipeline invalid inputs.
- In-memory run store transitions.
- SQL project repository persistence và progress.
- Folder structure preservation.
- Upload path traversal rejection.
- Raw input deletion không xóa promoted DOCX.
- Multipart folder upload.
- Background fake pipeline chuyển `COMPLETED`.
- DOCX download.
- Thiếu `sample_issues.json` chuyển `FAILED`.

Các kiểm tra khác đã pass:

```text
python -m compileall backend/app backend/tests
pip check
git diff --check
ASGI health: HTTP 200
OpenAPI: đủ 6 project endpoints
```

Default tests không gọi live LLM.

## 9. Checklist chuyển code sang VPS

### 9.1 Trước khi chuyển

Worktree hiện có nhiều file `D` ở root và `backend/`, `frontend/` đang là
untracked vì đây là một lần move/restructure lớn.

Phải kiểm tra:

```bash
git status
git diff --check
pytest -q backend/tests
```

Nếu chuyển bằng Git, cần stage/commit toàn bộ restructure. Nếu chỉ push các
file tracked cũ mà không add `backend/` và `frontend/`, VPS sẽ thiếu source mới.

Không commit:

- `backend/.env`
- API keys.
- `backend/.runtime/`
- Generated DOCX.
- Local database.

### 9.2 Không tái sử dụng `.venv` macOS

`backend/.venv` hiện được tạo trên macOS. Binary trong đó không chạy trên VPS
Linux.

Trên VPS:

```bash
cd /path/to/ia_audit_report
python3 --version
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
```

Yêu cầu Python 3.11 trở lên vì code dùng `enum.StrEnum`.

### 9.3 PostgreSQL

Tạo database/user theo policy của VPS, sau đó cấu hình:

```dotenv
DATABASE_URL=postgresql+psycopg://audit_user:strong-password@127.0.0.1:5432/audit_report
```

Không expose PostgreSQL ra public internet nếu không cần.

### 9.4 Storage

Tạo thư mục riêng ngoài source tree:

```bash
sudo mkdir -p /var/lib/ia-audit-report/projects
sudo chown -R <service-user>:<service-group> /var/lib/ia-audit-report
sudo chmod 750 /var/lib/ia-audit-report/projects
```

`.env`:

```dotenv
PROJECT_STORAGE_ROOT=/var/lib/ia-audit-report/projects
RAW_UPLOAD_RETENTION_DAYS=7
```

Audit documents có thể nhạy cảm. Production cần:

- Disk encryption hoặc encrypted object storage.
- Service user riêng.
- Directory permission chặt.
- Backup policy cho output/database.
- Không ghi file content vào application log.

### 9.5 Environment mẫu

```dotenv
ANTHROPIC_URI_ENDPOINT=https://...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=...

DATABASE_URL=postgresql+psycopg://...
PROJECT_STORAGE_ROOT=/var/lib/ia-audit-report/projects
RAW_UPLOAD_RETENTION_DAYS=7
UPLOAD_MAX_FILES=500
UPLOAD_MAX_BYTES=1073741824

API_CORS_ORIGINS=https://audit.example.com
API_RUN_WORKERS=1
```

### 9.6 Verify trên VPS

```bash
source backend/.venv/bin/activate
pytest -q backend/tests
uvicorn api:app \
  --app-dir backend \
  --host 127.0.0.1 \
  --port 8000
```

Sau đó:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/openapi.json
```

Nên để Uvicorn listen localhost và đặt Nginx/Caddy phía trước để terminate
HTTPS, giới hạn upload size và timeout.

## 10. Frontend hiện tại

`frontend/` hiện chỉ có:

- Feature-module folder skeleton.
- Test folder skeleton.
- Logo và các design reference trong `frontend/design/`.

Chưa có:

- `package.json`.
- Vue/Vite application.
- Router/store/API client.
- Component implementation.
- Frontend tests.

Không nên build các module `observations` và `issues` trong POC dù folder
placeholder đang tồn tại.

Frontend task tiếp theo:

1. Initialize Vue 3 + Vite + TypeScript.
2. Tạo một Projects page responsive.
3. Project list + detail panel.
4. Folder picker dùng `webkitdirectory`.
5. Multipart upload với `files`/`relative_paths`.
6. SSE progress timeline.
7. `COMPLETED`/`FAILED` terminal states.
8. Download DOCX.
9. API error/correlation ID display.

## 11. Known limitations và technical debt

### P0 — cần xử lý trước production

- Background job dùng thread trong API process.
- Restart server có thể làm project đang `PROCESSING` bị treo trạng thái.
- Nhiều API instances có thể xử lý workflow không nhất quán.
- Chưa có durable queue/worker hoặc startup recovery.
- Chưa có Alembic migrations.
- Chưa có authentication/authorization/project ownership.
- Local storage chưa mã hóa ở application layer.
- Cleanup chỉ chạy lúc application startup.
- Chưa có reverse-proxy/deployment config trong repository.

### P1 — POC correctness/usability

- Pipeline vẫn bắt buộc `sample_issues.json`.
- Chưa có retry/re-upload trên cùng project.
- Chưa có cancel project.
- Chưa validate MIME/extension allowlist.
- Chưa có content hash/deduplication.
- Chưa có pagination/filter cho project list.
- Chưa có upload progress riêng từ browser tới server; live events bắt đầu rõ
  nhất sau khi server lưu xong multipart request.
- Legacy `/runs` vẫn in-memory.

### P2 — production integrations

- Chưa có SharePoint/Microsoft Graph adapter.
- Chưa có S3/object store adapter.
- Chưa có SQS/Celery worker.
- Chưa có Bedrock adapter.
- Chưa có structured logging/metrics/tracing.
- Chưa có antivirus/malware scanning.

## 12. Thứ tự công việc đề xuất

### Nếu mục tiêu là demo POC trên VPS

1. Commit/push đầy đủ restructure.
2. Recreate Linux virtualenv.
3. Cấu hình PostgreSQL và secure storage.
4. Chạy tests.
5. Chạy backend sau HTTPS reverse proxy.
6. Initialize frontend.
7. Implement Projects screen.
8. Test một project folder thật end-to-end với LLM.

### Nếu mục tiêu là production foundation

1. Thêm Alembic.
2. Thêm authentication và project authorization.
3. Tách worker khỏi API process.
4. Thêm recovery/idempotency.
5. Chuyển storage sang S3/object store.
6. Thêm retention scheduler/lifecycle.
7. Thêm SharePoint adapter.
8. Thêm observability và security scanning.

Không nên bắt đầu Observation/Draft Review screens trước khi upload,
processing, terminal status và DOCX download hoạt động ổn định end-to-end.

## 13. Ghi chú cho coding agent tiếp theo

Repository root có `AGENTS.md` yêu cầu dùng GitNexus impact analysis trước khi
sửa symbol và `gitnexus_detect_changes()` trước commit.

Trong phiên refactor gần nhất:

- GitNexus MCP tools không được expose.
- Các file skill được `AGENTS.md` tham chiếu cũng không tồn tại tại path ghi
  trong file.
- Impact analysis đã được làm thủ công bằng caller/import search.
- Không có HIGH/CRITICAL blast radius được phát hiện.
- Chưa tạo commit.

Agent/session tiếp theo nên:

1. Kiểm tra GitNexus index/tool availability.
2. Chạy impact analysis trước khi sửa function/class/method.
3. Không dùng find-and-replace để rename symbol.
4. Chạy detect changes trước commit nếu tool khả dụng.
5. Giữ API project contract hiện tại để frontend không bị vỡ.
