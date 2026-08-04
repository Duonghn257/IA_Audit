# Trạng thái Backend

> Xác minh gần nhất: 03/08/2026
> Trạng thái bàn giao: POC đã triển khai
> Source of truth: `backend/app/`

## Kết quả hiện tại

FastAPI backend nhận audit folder, lưu project state và progress events, chạy
audit pipeline tám bước trong background, sau đó cho tải DOCX nếu xử lý thành
công.

```text
FastAPI route
  → ProjectManager
  → project repository + project storage
  → background AuditPipeline
  → progress events + terminal project state
```

API và compatibility CLI cùng dùng `AuditPipeline`; FastAPI không gọi CLI
entrypoint.

## Checklist chức năng

| Chức năng | Trạng thái | Bằng chứng trong source |
|---|---|---|
| Versioned FastAPI API | Đã xong | `backend/app/api/` |
| Validate/lưu folder upload | Đã xong | `project_files.py`, `project_storage.py` |
| Persistent project metadata | Đã xong | `project_repository.py` |
| Persistent progress events | Đã xong | `project_repository.py` |
| Background project execution | Đủ cho POC | `ThreadPoolExecutor` trong `ProjectManager` |
| SSE progress và heartbeat | Đã xong | `api/routes/projects.py` |
| Structured API errors | Đã xong | `api/errors.py`, correlation middleware |
| Audit pipeline tám bước | Đã xong | `application/audit_pipeline.py` |
| DOCX output download | Đã xong | Project output endpoint |
| PostgreSQL support | Đã xong | SQLAlchemy + psycopg |
| SQLite local fallback | Đã xong | Local development/tests |
| Alembic migration | Đã xong | Revision `20260729_01` |
| Authentication/authorization | Chưa làm | Bắt buộc trước production |
| Durable queue và recovery | Chưa làm | Worker hiện nằm trong API process |
| SharePoint/S3/SQS adapters | Chưa làm | Future integration scope |

## Project lifecycle

```text
UPLOADING → PROCESSING → COMPLETED
                    └──→ FAILED
UPLOADING ─────────────→ FAILED
```

Backend sở hữu status transitions và `allowed_actions`. Frontend không được tự
suy luận điều kiện export.

## Project API

| Method | Path | Mục đích |
|---|---|---|
| `POST` | `/api/v1/projects/upload` | Lưu folder và bắt đầu xử lý |
| `GET` | `/api/v1/projects` | Liệt kê projects |
| `GET` | `/api/v1/projects/{id}` | Đọc project snapshot hiện tại |
| `GET` | `/api/v1/projects/{id}/events` | Đọc durable events sau một ID |
| `GET` | `/api/v1/projects/{id}/events/stream` | Stream progress bằng SSE |
| `GET` | `/api/v1/projects/{id}/output` | Tải DOCX đã hoàn thành |
| `GET` | `/api/v1/health` | Service health |

`POST /projects/upload` trả HTTP 202, yêu cầu hai arrays `files` và
`relative_paths` có cùng độ dài, normalize relative path và từ chối unsafe
upload. Pipeline hiện tại còn yêu cầu `sample_issues.json` ở root folder.

Legacy `/api/v1/runs/*` vẫn được giữ để compatibility nhưng state còn nằm trong
memory; đây không phải flow POC chính.

## Pipeline tám bước

1. Parse project documents.
2. Build audit context.
3. Extract scope và constraints.
4. Draft issues qua LLM endpoint đã cấu hình.
5. Critique draft.
6. Tạo DOCX style specification.
7. Validate drafted issues.
8. Render và version DOCX output.

Live compatibility-CLI run với `data/lumina_grand` đã hoàn thành 8/8 bước,
draft một issue và tạo DOCX hợp lệ. Full-folder browser path tương đương vẫn là
roadmap item.

## Source map

| Khu vực | Vị trí |
|---|---|
| API bootstrap | `backend/api.py`, `backend/app/bootstrap/api.py` |
| Routes và schemas | `backend/app/api/` |
| Application orchestration | `backend/app/application/` |
| Project domain model | `backend/app/domain/projects.py` |
| SQLAlchemy persistence | `backend/app/infrastructure/` |
| Parsing/LLM/validation/rendering | `backend/app/pipeline/` |
| Migrations | `backend/alembic/` |
| Tests | `backend/tests/` |

## Baseline kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| Backend automated tests | 14 passed |
| Warning | 1 Starlette TestClient/httpx deprecation warning |
| Live Lumina Grand CLI pipeline | Hoàn thành 8/8 stages |
| Generated DOCX | Hợp lệ và mở được |
| API container health | Healthy |
| Alembic current | `20260729_01 (head)` |
| Alembic schema drift check | Pass |

Default tests không gọi live LLM:

```bash
cd backend
pytest
```

## Giới hạn hiện tại

- Restart API có thể để project `PROCESSING` bị treo.
- Pipeline chưa có durable checkpoint/resume theo stage.
- Local thread execution không phù hợp nhiều API replicas.
- Chưa có project ownership, authentication hoặc authorization.
- Upload có file-count/total-size limit nhưng chưa có MIME allowlist, antivirus
  scan hoặc content deduplication.
- Cleanup chạy khi startup, chưa có scheduler.
- Legacy run state còn nằm trong memory.
- `Base.metadata.create_all()` còn được giữ cho local compatibility; production
  nên quản lý schema chỉ bằng migrations.

## Khi nào cập nhật file này

Cập nhật khi API behavior, pipeline, persistence, backend tests hoặc giới hạn
thay đổi. Deployment details nằm tại [Infrastructure Status](INFRASTRUCTURE.md);
planned work nằm tại [roadmap](../roadmap/README.md).
