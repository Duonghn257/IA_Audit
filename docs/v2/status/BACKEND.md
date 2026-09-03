# Trạng thái Backend

> Xác minh gần nhất: 03/09/2026
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

Ngày 12/08, các helper của pipeline đã được tách theo responsibility mà không
đổi API behavior: AI client/prompt/validation nằm trong `app/ai`, parsing và
DOCX trong `app/documents`, còn context/retrieval boundary trong `app/rag`.

## Checklist chức năng

| Chức năng | Trạng thái | Bằng chứng trong source |
|---|---|---|
| Versioned FastAPI API | Đã xong | `backend/app/api/` |
| Upload-session local + validation | Đã xong | AWP/APM/PU/SOP và optional project `Samples/` |
| Persistent project metadata | Đã xong | `project_repository.py` |
| Persistent progress events | Đã xong | `project_repository.py` |
| Background project execution | Đủ cho POC | `ThreadPoolExecutor` trong `ProjectManager` |
| SSE progress và heartbeat | Đã xong | `api/routes/projects.py` |
| Structured API errors | Đã xong | `api/errors.py`, correlation middleware |
| Audit pipeline tám bước | Đã xong | `application/audit_pipeline.py` |
| DOCX output download | Đã xong | Versioned `/outputs/{output_id}/download` |
| Central Guidelines/template CRUD | Đã xong cho local UAT | `/central-knowledge`, overwrite hiện hành, immutable job snapshot |
| Versioned Audit job từ DB candidates | Đã xong cho UAT local worker | `audit_execution_service.py`, frozen issues/source/central knowledge, output revisions |
| PostgreSQL support | Đã xong | SQLAlchemy + psycopg |
| SQLite local fallback | Đã xong | Local development/tests |
| Alembic migration | Đã xong | Head `20260903_06` |
| Authentication/authorization | Chưa làm | Bắt buộc trước production |
| Durable queue và recovery | Chưa làm | Worker hiện nằm trong API process |
| S3 adapter | Chưa làm | Local intake adapter đang dùng cùng application port |

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

Upload-session UAT mới đã chạy bằng local adapter:

| Method | Path | Mục đích |
|---|---|---|
| `POST` | `/api/v1/upload-sessions` | Tạo manifest/session và upload URLs |
| `PUT` | `/api/v1/upload-sessions/{id}/files/{file_id}` | Upload raw file vào local staging |
| `GET` | `/api/v1/upload-sessions/{id}` | Đọc file status/validation report |
| `POST` | `/api/v1/upload-sessions/{id}/validate` | Hash, parse và logical-role validation |
| `POST` | `/api/v1/upload-sessions/{id}/projects` | Promote immutable source, tạo project + `v0.1` |
| `DELETE` | `/api/v1/upload-sessions/{id}` | Discard staging chưa promote |

Legacy `/api/v1/runs/*` đã được gỡ khỏi router/OpenAPI vì frontend UAT không
sử dụng. CLI nội bộ vẫn được giữ cho smoke test và vận hành cục bộ.

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
| Anthropic client, prompts và AI validation | `backend/app/ai/` |
| Parsing, template inspection và DOCX rendering | `backend/app/documents/` |
| RAG/context assembly | `backend/app/rag/` |
| Migrations | `backend/alembic/` |
| Tests | `backend/tests/` |

## Baseline kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| Backend automated tests | 32 passed |
| Import/compile check | Pass |
| Live Lumina Grand CLI pipeline | Hoàn thành 8/8 stages |
| Generated DOCX | Hợp lệ và mở được |
| API container health | Healthy |
| Alembic current | `20260827_05 (head)` |
| Alembic schema drift check | Pass |

Default tests không gọi live LLM:

```bash
cd backend
pytest
```

## Giới hạn hiện tại

- Restart API có thể để project `PROCESSING` bị treo.
- Pipeline chưa có durable checkpoint/resume theo stage; Audit retry chạy lại từ frozen input snapshot.
- Local thread execution không phù hợp nhiều API replicas.
- Chưa có project ownership, authentication hoặc authorization.
- Upload-session mới enforce DOCX/PDF/XLSX, tối đa 20 files và 100 MB;
  antivirus scan và content deduplication chưa có.
- Cleanup chạy khi startup, chưa có scheduler.
- `Base.metadata.create_all()` còn được giữ cho local compatibility; production
  nên quản lý schema chỉ bằng migrations.

## Khi nào cập nhật file này

Cập nhật khi API behavior, pipeline, persistence, backend tests hoặc giới hạn
thay đổi. Deployment details nằm tại [Infrastructure Status](INFRASTRUCTURE.md);
planned work nằm tại [roadmap](../roadmap/README.md).
