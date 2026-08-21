# API Documentation — IA Audit MVP v2

> Base URL: `/api/v1`  
> OpenAPI khi chạy ứng dụng: `/openapi.json`  
> Swagger UI: `/docs`  
> Cập nhật: 13/08/2026

## 1. Phạm vi và trạng thái

| Ký hiệu | Ý nghĩa |
|---|---|
| ✅ | Đã có API và xử lý backend |
| 🟡 | Contract/API đã có, nhưng chưa thể chạy trọn flow do thiếu S3 hoặc AI worker |
| ⏳ | API cũ của POC, vẫn giữ để không làm hỏng flow hiện tại |

Các endpoint 🟡 hiện trả HTTP `501 Not Implemented` cùng mã lỗi rõ ràng. Chúng được khai báo trước để frontend có thể thống nhất contract mà không giả vờ rằng backend đã xử lý được.

## 2. Quy ước chung

### Error response

```json
{
  "error": {
    "code": "VERSION_NOT_FOUND",
    "message": "Version not found: version-id",
    "details": {},
    "correlation_id": "request-correlation-id"
  }
}
```

Client có thể gửi `X-Correlation-ID`; nếu không gửi, API tự sinh và trả lại header này.

### Optimistic concurrency cho issue

Mỗi issue có `row_version`. Khi sửa hoặc disposition, frontend phải gửi lại giá trị đang thấy. Nếu dữ liệu đã bị request khác sửa trước đó, API trả:

```text
409 ROW_VERSION_CONFLICT
```

Frontend cần reload issue rồi cho người dùng thực hiện lại thay đổi.

### ID và thời gian

- ID là string UUID do backend sinh.
- Thời gian trả về theo ISO 8601 UTC.
- `project version` là workspace độc lập như `v0.1`, `v0.2`; chỉnh một version không làm thay đổi version khác.

## 3. Danh sách endpoint

### System

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| ✅ | `GET` | `/health` | Health check |

### Upload và tạo project theo flow v2

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| 🟡 | `POST` | `/upload-sessions` | Tạo staging session và presigned upload URLs |
| 🟡 | `GET` | `/upload-sessions/{session_id}` | Xem trạng thái upload/validation |
| 🟡 | `POST` | `/upload-sessions/{session_id}/validate` | Validate folder đã upload |
| 🟡 | `POST` | `/upload-sessions/{session_id}/projects` | Promote snapshot, tạo project và `v0.1` |
| 🟡 | `DELETE` | `/upload-sessions/{session_id}` | Hủy staging session |

Các API trên hiện trả `501 S3_STORAGE_NOT_CONFIGURED`. Chưa có bucket nên backend chưa thể tạo presigned URL hoặc promote source snapshot. Không có malware scan trong MVP theo quyết định hiện tại.

Tên project phải unique. Hai project được phép có toàn bộ file giống nhau nếu tên khác nhau; backend không deduplicate project theo hash nội dung.

Request dự kiến để tạo upload session:

```json
{
  "files": [
    {
      "relative_path": "Evidence/access-review.xlsx",
      "size_bytes": 152340,
      "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
  ]
}
```

Request tạo project sau validation:

```json
{
  "name": "FY2026 Access Review"
}
```

### Project/version workspace

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| ✅ | `GET` | `/projects/{project_id}/versions` | Danh sách version của project |
| ✅ | `POST` | `/projects/{project_id}/versions` | Tạo `v0.N` mới từ một base version |
| ✅ | `GET` | `/projects/{project_id}/versions/{version_id}` | Chi tiết workspace của version |

Request tạo version mới:

```json
{
  "base_version_id": "8b59171f-37df-44f3-b1a1-6238f12403c1"
}
```

Backend copy issue và source reference từ base version, nhưng không copy output DOCX. Số version được cấp theo project: `v0.1`, `v0.2`, `v0.3`, ...

Response rút gọn:

```json
{
  "version_id": "f325ca32-98a6-46bb-8ad4-b7231828de98",
  "project_id": "project-id",
  "sequence_no": 2,
  "label": "v0.2",
  "base_version_id": "8b59171f-37df-44f3-b1a1-6238f12403c1",
  "state": "DRAFT",
  "issue_revision": 4,
  "issue_counts": {"APPROVED": 2, "DRAFT": 1},
  "latest_job": null,
  "output_available": false,
  "allowed_actions": ["CREATE_VERSION", "VIEW_ISSUES", "EDIT_ISSUES", "RUN_DISCOVERY", "RUN_AUDIT"],
  "created_at": "2026-08-13T04:00:00Z",
  "updated_at": "2026-08-13T04:00:00Z"
}
```

Lưu ý: các API này đã chạy trên database, nhưng project/v0.1 mới chưa thể được tạo từ public flow v2 cho tới khi S3 upload được cấu hình.

### Issue register

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| ✅ | `GET` | `/projects/{project_id}/versions/{version_id}/issues` | Danh sách issue |
| ✅ | `POST` | `/projects/{project_id}/versions/{version_id}/issues` | Tạo manual issue |
| ✅ | `GET` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}` | Chi tiết issue |
| ✅ | `PUT` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}` | Cập nhật toàn bộ editable fields |
| ✅ | `POST` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}/disposition` | Duyệt/từ chối/yêu cầu evidence/out of scope |

Manual issue chỉ bắt buộc `observed_gap`:

```json
{
  "observed_gap": "Quarterly access review evidence was not retained.",
  "title_hint": "Access review evidence retention",
  "evidence_summary": null,
  "risk_category": null,
  "status": "DRAFT",
  "source_refs": []
}
```

Request cập nhật issue gửi đầy đủ editable fields và `row_version`:

```json
{
  "row_version": 1,
  "observed_gap": "Quarterly access review evidence was incomplete and not retained.",
  "title_hint": "Access review evidence retention",
  "evidence_summary": "One of four quarterly reviews was unavailable.",
  "risk_category": "Access Management",
  "status": "READY_FOR_REVIEW",
  "confidence": null,
  "validation_flags": [],
  "source_refs": []
}
```

Disposition hợp lệ:

```json
{
  "row_version": 2,
  "status": "APPROVED"
}
```

Các giá trị disposition được chấp nhận: `APPROVED`, `NEEDS_EVIDENCE`, `REJECTED`, `OUT_OF_SCOPE`.

Source reference có cấu trúc:

```json
{
  "ref_kind": "EVIDENCE",
  "document_id": "document-id",
  "unit_id": null,
  "location": {"sheet": "Access Review", "range": "A1:B12"},
  "quote": "Review completed by control owner"
}
```

Manual issue có thể không có source reference. Quy tắc AI candidate phải có cả `EVIDENCE` và `CRITERIA` sẽ được enforce khi AI discovery được implement.

### AI discovery và Audit

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| 🟡 | `POST` | `/projects/{project_id}/versions/{version_id}/discovery-jobs` | Tìm AI candidate issues |
| 🟡 | `POST` | `/projects/{project_id}/versions/{version_id}/audit-jobs` | Freeze issue revision, tạo Issue Log DOCX |

Discovery request:

```json
{
  "force": false
}
```

Audit request:

```json
{
  "issue_revision": 4
}
```

Hiện cả hai endpoint trả `501 AI_PIPELINE_NOT_IMPLEMENTED`. Contract response thành công dự kiến là `202` và một `JobResponse`. JSON schema chi tiết cho các AI artefact nội bộ như scope map, facts, candidate output và coverage matrix vẫn cần thảo luận riêng; chúng chưa được coi là contract đã chốt.

### Durable jobs

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| ✅ | `GET` | `/jobs/{job_id}` | Lấy trạng thái/progress job |
| ✅ | `GET` | `/jobs/{job_id}/events?after_event_id=0` | Poll progress events |
| ✅ | `GET` | `/jobs/{job_id}/events/stream?after_event_id=0` | Nhận progress bằng SSE |
| 🟡 | `POST` | `/jobs/{job_id}/retry` | Đưa terminal job về queue |

Repository và API job đã có persistence, event, lease/heartbeat và retry state. Chưa có process worker riêng để claim và thực thi AI job, vì vậy retry chỉ có ý nghĩa sau khi worker được implement.

Job response:

```json
{
  "job_id": "job-id",
  "project_id": "project-id",
  "project_version_id": "version-id",
  "job_type": "DISCOVERY",
  "state": "RUNNING",
  "stage": "PARSING",
  "completed_items": 3,
  "total_items": 10,
  "current_message": "Parsing source documents",
  "attempt_count": 1,
  "correlation_id": "correlation-id",
  "created_at": "2026-08-13T04:00:00Z",
  "updated_at": "2026-08-13T04:01:00Z",
  "heartbeat_at": "2026-08-13T04:01:00Z",
  "error": null
}
```

### Output revisions

| Trạng thái | Method | Path | Mục đích |
|---|---|---|---|
| ✅ | `GET` | `/projects/{project_id}/versions/{version_id}/outputs` | Danh sách DOCX revisions của version |
| 🟡 | `GET` | `/outputs/{output_id}/download` | Download/presigned URL cho DOCX |

Output metadata đã lưu theo revision. Download mới trả `501 S3_STORAGE_NOT_CONFIGURED` vì object chưa thể đặt trên private S3.

## 4. API POC đang giữ để tương thích

| Trạng thái | Method | Path | Ghi chú |
|---|---|---|---|
| ⏳ | `POST` | `/projects/upload` | Upload local và tự chạy pipeline cũ; không phải flow v2 |
| ⏳ | `GET` | `/projects` | Danh sách project theo model POC |
| ⏳ | `GET` | `/projects/{project_id}` | Chi tiết project theo model POC |
| ⏳ | `GET` | `/projects/{project_id}/events` | Progress POC |
| ⏳ | `GET` | `/projects/{project_id}/events/stream` | SSE progress POC |
| ⏳ | `GET` | `/projects/{project_id}/output` | Download output local của POC |
| ⏳ | `POST` | `/runs` | Chạy pipeline theo local paths |
| ⏳ | `GET` | `/runs`, `/runs/{run_id}` | Theo dõi run cũ |
| ⏳ | `GET` | `/runs/{run_id}/events` | Poll event run cũ |
| ⏳ | `GET` | `/runs/{run_id}/events/stream` | SSE run cũ |
| ⏳ | `GET` | `/runs/{run_id}/output` | Download output run cũ |

Không nên build frontend v2 mới dựa trên nhóm POC này. Chúng được giữ tạm thời để tránh làm hỏng demo hiện có và sẽ được retire sau khi upload session + S3 + worker v2 chạy end-to-end.

## 5. Mã lỗi chính

| HTTP | Code | Khi nào xảy ra |
|---:|---|---|
| `404` | `PROJECT_NOT_FOUND` | Không tìm thấy project |
| `404` | `VERSION_NOT_FOUND` | Không tìm thấy version hoặc version không thuộc project |
| `404` | `ISSUE_NOT_FOUND` | Không tìm thấy issue trong version |
| `404` | `JOB_NOT_FOUND` | Không tìm thấy job |
| `409` | `ROW_VERSION_CONFLICT` | Update bằng `row_version` cũ |
| `409` | `ACTIVE_JOB_CONFLICT` | Job tương đương đang queued/running |
| `409` | `INVALID_STATE` | Workflow transition không hợp lệ |
| `422` | `INVALID_REQUEST` | Domain validation thất bại |
| `501` | `S3_STORAGE_NOT_CONFIGURED` | Endpoint cần S3 nhưng bucket chưa sẵn sàng |
| `501` | `AI_PIPELINE_NOT_IMPLEMENTED` | Endpoint cần AI pipeline/worker chưa implement |

## 6. Phần cần thảo luận tiếp

- JSON schema versioned cho `scope_map`, evidence facts, AI candidates, coverage matrix, validation report và run manifest.
- Quy tắc preflight chính xác trước khi Audit, nhất là issue nào được đưa vào DOCX.
- Central Guideline/template metadata và cách chọn version.
- Response chính thức của upload session gồm multipart hay một presigned URL cho mỗi file.

Các phần trên chưa chặn việc frontend tích hợp version/issue register và job progress contract hiện tại.
