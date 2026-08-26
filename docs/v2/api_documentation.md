# UAT API Contract — Operation Report Jedi

> Contract version: `1.1.0-uat`
> Base URL: `/api/v1`  
> Content type mặc định: `application/json`
> OpenAPI runtime: `/openapi.json`
> Swagger UI: `/docs`  
> Cập nhật: 26/08/2026

## 1. Mục đích và phạm vi

Tài liệu này là contract đích giữa frontend, backend và worker cho bản UAT. Mỗi
API đều nêu rõ mục đích, input, output, HTTP status và lỗi nghiệp vụ quan trọng.

Contract bao phủ toàn bộ luồng UAT:

1. upload folder vào staging;
2. validate và tạo project cùng version `v0.1`;
3. xem project và lịch sử version;
4. chạy AI discovery;
5. review, sửa và disposition issue;
6. chạy Audit để tạo DOCX;
7. theo dõi background job;
8. tải output theo version.

UAT không có API để sửa source file sau khi project được tạo, chỉnh nội dung
DOCX trên web, cancel job, merge/split issue hoặc publish report ra hệ thống
ngoài.

### 1.1 Trạng thái triển khai

| Trạng thái | Ý nghĩa |
|---|---|
| **READY** | Route và xử lý backend hiện đã có |
| **STUB** | Route đã xuất hiện trong OpenAPI nhưng hiện trả `501` |
| **TARGET** | Contract UAT đã chốt trong tài liệu, backend còn phải hoàn thiện |
| **BRIDGE** | API tạm thời mà frontend UAT hiện tại còn dùng; không dùng cho client mới |

Các section 2–10 mô tả contract UAT đích. Section 11 ghi rõ chênh lệch giữa
contract đích với runtime hiện tại và các API bridge cần retire.

## 2. Quy ước chung

### 2.1 Header

| Header | Bắt buộc | Áp dụng | Ý nghĩa |
|---|---:|---|---|
| `Accept: application/json` | Có | API JSON | Định dạng response |
| `Content-Type: application/json` | Có | Request JSON | Định dạng request |
| `X-Correlation-ID` | Không | Mọi request | Client truyền ID để trace; backend tự sinh nếu thiếu và luôn trả lại |
| `Idempotency-Key` | Có | Command tạo/promote/start/retry | Retry cùng key không được tạo resource hoặc job trùng |
| `Last-Event-ID` | Không | SSE | Resume stream sau event cuối client đã nhận |

Internal UAT chưa có application login/RBAC. Môi trường phải được bảo vệ bằng
corporate VPN hoặc approved IP range. Đây không phải quyết định cho production.

### 2.2 ID, thời gian và JSON

- JSON dùng `snake_case`.
- ID là opaque string; client không parse hoặc tự sinh ID server resource.
- Timestamp là ISO 8601 UTC, ví dụ `2026-08-21T08:15:30Z`.
- Field optional không có giá trị trả `null`; không dùng chuỗi rỗng thay
  `null`.
- Client phải bỏ qua response field chưa biết để hỗ trợ additive change.
- Breaking change cần base path mới hoặc major contract version mới.

### 2.3 Error response

Mọi lỗi nghiệp vụ do API kiểm soát dùng một shape:

```json
{
  "error": {
    "code": "ROW_VERSION_CONFLICT",
    "message": "Issue was changed by another request. Reload it and retry.",
    "details": {
      "current_row_version": 8
    },
    "correlation_id": "6d7849f8-1bd8-46a3-aa52-a5950e3b15cb"
  }
}
```

| HTTP | Ý nghĩa |
|---:|---|
| `400` | Request không parse được hoặc protocol không hợp lệ |
| `404` | Resource không tồn tại hoặc không thuộc parent trong URL |
| `409` | Duplicate, stale version hoặc workflow conflict |
| `410` | Artefact từng tồn tại nhưng đã hết retention |
| `413` | Upload vượt tổng dung lượng cho phép |
| `415` | File/content type không được hỗ trợ |
| `422` | Request đúng JSON nhưng vi phạm validation/business rule |
| `429` | Rate/concurrency limit |
| `500` | Lỗi backend không dự kiến |
| `501` | Route contract đã publish nhưng capability chưa được cấu hình/implement |
| `503` | Dependency tạm thời không sẵn sàng |

### 2.4 Pagination

Endpoint list lớn dùng cursor:

```json
{
  "items": [],
  "page": {
    "next_cursor": null,
    "has_more": false
  }
}
```

Query chung:

| Field | Type | Default | Rule |
|---|---|---:|---|
| `limit` | integer | `50` | `1..100` |
| `cursor` | string | `null` | Opaque cursor do server trả |

List version và output của một project dự kiến nhỏ nên trả array, không
paginate trong UAT.

### 2.5 Optimistic concurrency

Mỗi issue có `row_version`. `PATCH issue` và `disposition` phải gửi đúng
`row_version` client đang thấy. Nếu issue đã bị request khác sửa, API trả
`409 ROW_VERSION_CONFLICT`; client reload issue rồi cho người dùng thử lại.

Mỗi thay đổi issue làm tăng:

- `issue.row_version` của issue đó;
- `project_version.issue_revision` của workspace.

Audit request phải gửi `issue_revision` để đóng băng đúng issue set.

### 2.6 Background command và idempotency

Discovery, Audit, validate và retry không chờ xử lý hoàn tất. API trả `202`
cùng job/session snapshot. Client poll hoặc dùng SSE để theo dõi.

Với cùng scope và `Idempotency-Key`:

- nếu command trước đã được nhận, trả lại resource/job đã tạo;
- không tạo duplicate version, job hoặc output;
- một active job tương đương có thể trả `409 ACTIVE_JOB_CONFLICT` kèm
  `job_id` đang chạy.

## 3. Danh mục API UAT đích

### 3.1 System và intake

| Status | Method | Path | Mục đích | Success |
|---|---|---|---|---|
| READY | `GET` | `/health` | Kiểm tra API process | `200 HealthResponse` |
| READY | `POST` | `/upload-sessions` | Tạo staging session và upload instructions | `201 UploadSession` |
| READY | `PUT` | `/upload-sessions/{session_id}/files/{file_id}` | Upload raw file content vào local staging | `200 UploadFile` |
| READY | `GET` | `/upload-sessions/{session_id}` | Đọc trạng thái, tree và validation report | `200 UploadSession` |
| READY | `POST` | `/upload-sessions/{session_id}/validate` | Validate/revalidate file đã upload | `200 UploadSession` |
| READY | `POST` | `/upload-sessions/{session_id}/projects` | Promote snapshot, tạo project và `v0.1` | `201 CreateProjectFromUploadResponse` |
| READY | `DELETE` | `/upload-sessions/{session_id}` | Hủy staging chưa promote | `204` |

### 3.2 Project, version và issue workspace

| Status | Method | Path | Mục đích | Success |
|---|---|---|---|---|
| TARGET | `GET` | `/projects` | List/search project | `200 ProjectPage` |
| TARGET | `GET` | `/projects/{project_id}` | Project detail và source/version summary | `200 ProjectDetail` |
| READY | `GET` | `/projects/{project_id}/source-documents` | Cây immutable source theo folder/file | `200 SourceTree` |
| READY | `GET` | `/projects/{project_id}/versions` | List audit version | `200 ProjectVersion[]` |
| READY | `POST` | `/projects/{project_id}/versions` | Tạo `v0.N` từ base version | `201 ProjectVersion` |
| READY | `GET` | `/projects/{project_id}/versions/{version_id}` | Workspace snapshot của version | `200 ProjectVersion` |
| TARGET | `GET` | `/projects/{project_id}/versions/{version_id}/issues` | List/filter issue | `200 IssuePage` |
| READY | `POST` | `/projects/{project_id}/versions/{version_id}/issues` | Tạo manual issue | `201 Issue` |
| READY | `GET` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}` | Đọc một issue | `200 Issue` |
| TARGET | `PATCH` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}` | Autosave business fields | `200 Issue` |
| TARGET | `POST` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}/disposition` | Ghi quyết định review | `200 Issue` |

### 3.3 Discovery, Audit, job và output

| Status | Method | Path | Mục đích | Success |
|---|---|---|---|---|
| READY | `POST` | `/projects/{project_id}/versions/{version_id}/discovery-jobs` | Enqueue Discovery qua injectable AI adapter | `202 Job` |
| STUB | `POST` | `/projects/{project_id}/versions/{version_id}/audit-jobs` | Freeze input và tạo Issue Log DOCX | `202 Job` |
| READY | `GET` | `/jobs/{job_id}` | Đọc job snapshot/progress | `200 Job` |
| READY | `GET` | `/jobs/{job_id}/events` | Poll durable events | `200 JobEvent[]` |
| READY | `GET` | `/jobs/{job_id}/events/stream` | Stream durable events bằng SSE | `200 text/event-stream` |
| READY | `POST` | `/jobs/{job_id}/retry` | Retry job `FAILED`/`INCOMPLETE` an toàn | `202 Job` |
| READY | `GET` | `/projects/{project_id}/versions/{version_id}/outputs` | List immutable output revisions | `200 OutputRevision[]` |
| TARGET | `GET` | `/projects/{project_id}/versions/{version_id}/outputs/{output_id}/download` | Tải DOCX thuộc đúng project/version | `200 DOCX` hoặc `302` |

## 4. Shared data contracts

### 4.1 UploadSession

```json
{
  "session_id": "upl_01J5...",
  "state": "READY_TO_CREATE",
  "created_at": "2026-08-21T08:00:00Z",
  "expires_at": "2026-08-22T08:00:00Z",
  "files": [
    {
      "file_id": "fil_01J5...",
      "relative_path": "AWP/Approved Work Programme.pdf",
      "size_bytes": 152340,
      "content_type": "application/pdf",
      "upload_status": "UPLOADED",
      "logical_role": "SCOPE",
      "readability_status": "READABLE",
      "validation_message": null,
      "upload_method": "PUT",
      "upload_url": "/api/v1/upload-sessions/upl_01J5.../files/fil_01J5...",
      "required_headers": {"Content-Type": "application/pdf"}
    }
  ],
  "validation_report": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "role_summary": {
      "SCOPE": 1,
      "RISK_CONTEXT": 1,
      "EVIDENCE": 4,
      "CRITERIA": 2
    }
  },
  "allowed_actions": ["CREATE_PROJECT", "DISCARD"],
  "action_reasons": {}
}
```

Upload session states:
`UPLOADING | VALIDATING | READY_TO_CREATE | INVALID | PROMOTED | EXPIRED`.

Logical roles:
`SCOPE | RISK_CONTEXT | EVIDENCE | CRITERIA | CONTEXT`.

Validation message:

| Field | Type | Ý nghĩa |
|---|---|---|
| `code` | string | Stable machine-readable code |
| `message` | string | Nội dung cho người dùng |
| `file_id` | string/null | File liên quan |
| `relative_path` | string/null | Path để UI highlight |
| `blocking` | boolean | Có chặn Create project không |
| `details` | object | Dữ liệu bổ sung có cấu trúc |

### 4.2 ProjectDetail

```json
{
  "project_id": "prj_01J5...",
  "name": "FY2026 Access Review",
  "state": "READY_FOR_DISCOVERY",
  "source_snapshot": {
    "snapshot_id": "src_01J5...",
    "document_count": 8,
    "total_size_bytes": 4823130,
    "created_at": "2026-08-21T08:10:00Z"
  },
  "current_version_id": "ver_01J5...",
  "version_count": 1,
  "latest_version": {
    "version_id": "ver_01J5...",
    "label": "v0.1",
    "state": "DRAFT"
  },
  "allowed_actions": ["VIEW_VERSIONS", "CREATE_VERSION"],
  "action_reasons": {
    "RUN_DISCOVERY": "Select a project version first."
  },
  "created_at": "2026-08-21T08:10:00Z",
  "updated_at": "2026-08-21T08:10:00Z"
}
```

Project states:
`READY_FOR_DISCOVERY | CANDIDATES_AVAILABLE | OUTPUT_AVAILABLE`.

### 4.3 SourceTree

```json
{
  "snapshot_id": "src_01J5...",
  "status": "FROZEN",
  "folder_count": 4,
  "file_count": 8,
  "total_size_bytes": 4823130,
  "folders": [
    {
      "name": "AWP",
      "logical_role": "SCOPE",
      "file_count": 2,
      "files": [
        {
          "document_id": "doc_01J5...",
          "name": "Approved Work Programme.pdf",
          "relative_path": "AWP/Approved Work Programme.pdf",
          "logical_role": "SCOPE",
          "size_bytes": 152340,
          "content_type": "application/pdf",
          "status": "READY",
          "parse_status": "PENDING"
        }
      ]
    }
  ]
}
```

Folder được nhóm theo logical role và sắp theo thứ tự SCOPE (AWP),
RISK_CONTEXT (APM), EVIDENCE (Process Understanding), rồi CRITERIA
(Process SOP). Chỉ folder thực sự có document được trả về. File trong mỗi
folder được sắp theo relative path.

`status = READY` nghĩa là file đã qua validation và nằm trong immutable
snapshot; `parse_status` phản ánh trạng thái artefact dẫn xuất của discovery.

### 4.4 ProjectVersion

```json
{
  "version_id": "ver_01J5...",
  "project_id": "prj_01J5...",
  "sequence_no": 2,
  "label": "v0.2",
  "base_version_id": "ver_01J4...",
  "state": "DRAFT",
  "issue_revision": 0,
  "created_by_user_id": "usr_01J5...",
  "created_by_name": "UAT Auditor",
  "issue_counts": {},
  "latest_job": null,
  "output_available": false,
  "output_status": null,
  "allowed_actions": [
    "CREATE_VERSION",
    "VIEW_ISSUES",
    "EDIT_ISSUES",
    "RUN_DISCOVERY",
    "RUN_AUDIT"
  ],
  "created_at": "2026-08-21T09:00:00Z",
  "updated_at": "2026-08-21T09:30:00Z"
}
```

Version states:
`DRAFT | CANDIDATES_READY | AUDITING | DOCX_READY | STALE_OUTPUT`.

Version mới dùng chung immutable source snapshot của project và lưu
`base_version_id` để truy vết, nhưng không copy candidate issues, source
references, jobs hoặc outputs từ base version. Version luôn bắt đầu ở
`DRAFT`, `issue_revision = 0` và `issue_counts = {}`. Sequence được cấp ở
cấp project: `v0.1`, `v0.2`, ...

### 4.5 Issue và SourceReference

```json
{
  "issue_id": "iss_01J5...",
  "project_version_id": "ver_01J5...",
  "origin": "AI_DISCOVERED",
  "status": "READY_FOR_REVIEW",
  "observed_gap": "Quarterly access review evidence was not retained.",
  "title_hint": "Access review evidence retention",
  "evidence_summary": "One of four quarterly review packages was unavailable.",
  "evidence_refs": [
    "Process Understanding/Access Review.xlsx - Sheet Review"
  ],
  "sop_refs": [
    "Process SOP/Access Review SOP.docx - Section 3.2"
  ],
  "risk_category": "Access Management",
  "confidence": 0.86,
  "validation_flags": [],
  "row_version": 3,
  "source_refs": [
    {
      "reference_id": "ref_01J5...",
      "ref_kind": "EVIDENCE",
      "document_id": "doc_01J5...",
      "unit_id": "unit_01J5...",
      "location": {
        "sheet": "Access Review",
        "range": "A1:B12"
      },
      "quote": "Review completed by control owner"
    }
  ],
  "created_at": "2026-08-21T09:05:00Z",
  "updated_at": "2026-08-21T09:20:00Z"
}
```

| Field | Rule |
|---|---|
| `origin` | `AI_DISCOVERED | MANUAL`; không đổi sau khi tạo |
| `status` | `DRAFT | READY_FOR_REVIEW | APPROVED | NEEDS_EVIDENCE | REJECTED | OUT_OF_SCOPE` |
| `observed_gap` | Required, không được blank |
| `title_hint` | AI candidate required; manual draft optional |
| `evidence_summary` | AI candidate required; manual issue optional |
| `risk_category` | Optional |
| `confidence` | `0..1`, AI-owned; manual issue có thể `null` |
| `evidence_refs` | Discovery candidate cần ít nhất một evidence reference string |
| `sop_refs` | Discovery candidate cần ít nhất một SOP/criteria reference string |
| `source_refs` | Compatibility view cho client cũ; frontend mới tự gộp hai mảng trên khi cần hiển thị |
| `location` | Object theo loại file: page/section hoặc sheet/range |
| `quote` | Optional short excerpt; không thay thế document provenance |

### 4.6 Job và JobEvent

```json
{
  "job_id": "job_01J5...",
  "project_id": "prj_01J5...",
  "project_version_id": "ver_01J5...",
  "job_type": "DISCOVERY",
  "state": "RUNNING",
  "stage": "PARSING",
  "completed_items": 3,
  "total_items": 10,
  "current_message": "Parsing source documents",
  "attempt_count": 1,
  "correlation_id": "6d7849f8-1bd8-46a3-aa52-a5950e3b15cb",
  "created_at": "2026-08-21T09:00:00Z",
  "updated_at": "2026-08-21T09:01:00Z",
  "heartbeat_at": "2026-08-21T09:01:00Z",
  "error": null
}
```

Job type: `DISCOVERY | AUDIT`.

Job state: `QUEUED | RUNNING | SUCCEEDED | INCOMPLETE | FAILED`.

```json
{
  "event_id": 17,
  "job_id": "job_01J5...",
  "stage": "PARSING",
  "message": "Parsed 3 of 10 documents",
  "completed_items": 3,
  "total_items": 10,
  "warning": false,
  "occurred_at": "2026-08-21T09:01:00Z"
}
```

### 4.7 OutputRevision

```json
{
  "output_id": "out_01J5...",
  "project_version_id": "ver_01J5...",
  "ordinal": 2,
  "status": "CURRENT",
  "filename": "FY2026 Access Review_Issue Log v0.2.docx",
  "content_hash": "sha256:4cd8...",
  "created_at": "2026-08-21T10:00:00Z",
  "download_url": "/api/v1/projects/prj_01J5.../versions/ver_01J5.../outputs/out_01J5.../download"
}
```

Output status: `CURRENT | STALE`. Mỗi Audit thành công tạo một immutable
revision; re-Audit không ghi đè file cũ.

## 5. System API

### 5.1 GET `/health`

**Mục đích:** liveness check cho load balancer, deployment và smoke test.

**Input:** không có path/query/body.

**Output — `200`:**

```json
{
  "status": "ok",
  "service": "operation-report-jedi-backend",
  "version": "2.0.0"
}
```

Health không kiểm tra sâu database/storage/AI. Nếu cần readiness, bổ sung route
riêng thay vì thay đổi semantics của route này.

## 6. Upload và project intake APIs

Các API dưới đây hiện chạy bằng local filesystem adapter. Client nhận
`upload_url` từ response và không phụ thuộc storage backend; khi chuyển sang
S3, URL này sẽ trở thành presigned URL mà không đổi create/get/validate/promote
flow.

### 6.1 POST `/upload-sessions`

**Mục đích:** khai báo folder manifest và tạo staging session. Request này chưa
tạo project và chưa chạy discovery.

**Input:**

```json
{
  "files": [
    {
      "relative_path": "AWP/Approved Work Programme.docx",
      "size_bytes": 152340,
      "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "modified_at": "2026-08-20T03:00:00Z"
    }
  ]
}
```

| Field | Required | Rule |
|---|---:|---|
| `files` | Có | `1..20` files |
| `relative_path` | Có | POSIX relative path; không absolute, `..` hoặc duplicate |
| `size_bytes` | Có | `> 0`; tổng folder tối đa `100,000,000` bytes |
| `content_type` | Không | MIME metadata của DOCX/PDF/XLSX |
| `modified_at` | Không | Metadata từ browser |

**Output — `201 UploadSession`:** state `UPLOADING`; mỗi file có
`file_id`, `upload_method = "PUT"`, `upload_url`, required headers và
upload status.

Local adapter trả URL dạng:

```text
/api/v1/upload-sessions/{session_id}/files/{file_id}
```

**Lỗi chính:** `422 INVALID_REQUEST` cho folder rỗng, unsafe/duplicate path,
file rỗng, quá 20 files, quá 100 MB hoặc format ngoài DOCX/PDF/XLSX.

### 6.2 PUT `/upload-sessions/{session_id}/files/{file_id}`

**Mục đích:** upload raw content của một file vào local staging.

**Input:** raw request body; `Content-Type` nên trùng metadata đã khai báo.
Số byte thực tế phải bằng chính xác `size_bytes`.

**Output — `200 UploadFile`:** `upload_status = "UPLOADED"`.

**Lỗi chính:** `404 UPLOAD_SESSION_NOT_FOUND`,
`404 UPLOAD_FILE_NOT_FOUND`, `409 INVALID_STATE`,
`422 INVALID_REQUEST` khi size mismatch.

Route này là upload target của local adapter. Khi dùng S3, frontend PUT trực
tiếp vào presigned URL và route application này không nằm trên data path.

### 6.3 GET `/upload-sessions/{session_id}`

**Mục đích:** phục hồi wizard sau reload và đọc upload/validation status.

**Input:** path `session_id`.

**Output — `200 UploadSession`:** per-file status, validation report,
`allowed_actions` và `action_reasons`.

**Lỗi chính:** `404 UPLOAD_SESSION_NOT_FOUND`, `409 INVALID_STATE` nếu
session đã hết hạn.

### 6.4 POST `/upload-sessions/{session_id}/validate`

**Mục đích:** validation đồng bộ trên local storage sau khi upload file.

**Input:** path `session_id`; không có body.

**Output — `200 UploadSession`:** terminal state `READY_TO_CREATE` hoặc
`INVALID`, kèm structured validation report.

Validation hiện kiểm tra:

- object tồn tại và size khớp manifest;
- SHA-256 content hash;
- DOCX/PDF/XLSX parse được;
- logical-role mapping theo `AWP`, `APM`, `Process Understanding` và
  `Process SOP`;
- có ít nhất một readable file cho mỗi role `SCOPE`, `RISK_CONTEXT`,
  `EVIDENCE` và `CRITERIA`;
- file ngoài required folders được giữ là `CONTEXT` và sinh warning.

Session `INVALID` cho phép upload lại file rồi validate lại.

**Lỗi chính:** `404 UPLOAD_SESSION_NOT_FOUND`, `409 INVALID_STATE`.

### 6.5 POST `/upload-sessions/{session_id}/projects`

**Mục đích:** copy valid staging content sang immutable local source snapshot,
tạo project và `v0.1` trong cùng application flow.

**Input:**

```json
{
  "name": "FY2026 Access Review"
}
```

**Output — `201 CreateProjectFromUploadResponse`:**

```json
{
  "project_id": "project-id",
  "name": "FY2026 Access Review",
  "state": "READY_FOR_DISCOVERY",
  "source_snapshot_id": "snapshot-id",
  "version": {
    "version_id": "version-id",
    "sequence_no": 1,
    "label": "v0.1",
    "state": "DRAFT",
    "issue_revision": 0
  },
  "created_at": "2026-08-21T08:10:00Z",
  "updated_at": "2026-08-21T08:10:00Z"
}
```

**Lỗi chính:** `404 UPLOAD_SESSION_NOT_FOUND`,
`409 DUPLICATE_PROJECT_NAME`, `409 INVALID_STATE`.

Nếu database promotion lỗi, backend dọn local source copy và giữ staging để
người dùng có thể retry.

### 6.6 DELETE `/upload-sessions/{session_id}`

**Mục đích:** xóa metadata và local staging của session chưa promote.

**Input:** path `session_id`.

**Output — `204`:** không có body.

**Lỗi chính:** `404 UPLOAD_SESSION_NOT_FOUND`,
`409 INVALID_STATE` nếu session đã promote.

## 7. Project và version APIs

### 7.1 GET `/projects`

**Mục đích:** project list/search cho landing page.

**Input query:**

| Field | Type | Default | Ý nghĩa |
|---|---|---:|---|
| `search` | string | null | Tìm case-insensitive theo name |
| `state` | ProjectState | null | Filter state |
| `limit` | integer | 50 | Page size |
| `cursor` | string | null | Cursor trang tiếp theo |

**Output — `200 ProjectPage`:** `items` là ProjectDetail rút gọn (không có
full source tree), kèm `page`.

### 7.2 GET `/projects/{project_id}`

**Mục đích:** tải project header, immutable source summary và version summary.

**Input:** path `project_id`.

**Output — `200 ProjectDetail`.**

**Lỗi chính:** `404 PROJECT_NOT_FOUND`.

### 7.3 GET `/projects/{project_id}/source-documents`

**Mục đích:** tải immutable source tree cho tab **Source & discovery**, gồm
folder, file, logical role và trạng thái xử lý.

**Input:** path `project_id`.

**Output — `200 SourceTree`:** folder theo thứ tự role nghiệp vụ; file trong
mỗi folder sort theo `relative_path`. Response không trả object key hoặc
content hash nội bộ.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`. Project của user khác cũng trả
`PROJECT_NOT_FOUND` để tránh cross-project disclosure.

### 7.4 GET `/projects/{project_id}/versions`

**Mục đích:** hiển thị version history và cho người dùng quay lại version cũ.

**Input:** path `project_id`.

**Output — `200 ProjectVersion[]`:** sort `sequence_no DESC`.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`.

### 7.5 POST `/projects/{project_id}/versions`

**Mục đích:** xử lý nút **+ New audit**; tạo next `v0.N` từ base đang chọn.

**Headers:** `Idempotency-Key` required theo target contract; runtime chưa
enforce header này (xem mục 12).

**Input:**

```json
{
  "base_version_id": "ver_01J4..."
}
```

**Output — `201 ProjectVersion`:**

```json
{
  "version_id": "ver_01J5...",
  "project_id": "prj_01J5...",
  "sequence_no": 2,
  "label": "v0.2",
  "base_version_id": "ver_01J4...",
  "state": "DRAFT",
  "issue_revision": 0,
  "created_by_user_id": "usr_01J5...",
  "created_by_name": "UAT Auditor",
  "issue_counts": {},
  "latest_job": null,
  "output_available": false,
  "output_status": null,
  "allowed_actions": [
    "CREATE_VERSION",
    "VIEW_ISSUES",
    "EDIT_ISSUES",
    "RUN_DISCOVERY",
    "RUN_AUDIT"
  ],
  "created_at": "2026-08-26T09:00:00Z",
  "updated_at": "2026-08-26T09:00:00Z"
}
```

Version mới chỉ kế thừa immutable source snapshot và lưu liên kết
`base_version_id`. Candidate issues, source references, jobs và outputs đều
rỗng; frontend không được hiển thị issue của base version trong workspace mới.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`,
`409 IDEMPOTENCY_CONFLICT`, `422 INVALID_BASE_VERSION`.

### 7.6 GET `/projects/{project_id}/versions/{version_id}`

**Mục đích:** tải workspace state, issue revision, counts, latest job và allowed
actions của một version.

**Input:** path `project_id`, `version_id`.

**Output — `200 ProjectVersion`.**

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`. Một
`version_id` tồn tại nhưng không thuộc `project_id` vẫn trả
`VERSION_NOT_FOUND` để tránh cross-project disclosure.

## 8. Issue APIs

### 8.1 GET `/projects/{project_id}/versions/{version_id}/issues`

**Mục đích:** tải Issue Register.

**Input query:**

| Field | Type | Default | Ý nghĩa |
|---|---|---:|---|
| `status` | IssueStatus[] | null | Filter một hoặc nhiều status |
| `origin` | IssueOrigin | null | `AI_DISCOVERED` hoặc `MANUAL` |
| `search` | string | null | Tìm trong title/gap |
| `limit` | integer | 50 | Page size |
| `cursor` | string | null | Cursor trang tiếp theo |

**Output — `200 IssuePage`:** `items: Issue[]` và `page`.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`.

### 8.2 POST `/projects/{project_id}/versions/{version_id}/issues`

**Mục đích:** tạo manual issue trong selected version.

**Headers:** `Idempotency-Key` required.

**Input:**

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

`observed_gap` là field duy nhất bắt buộc cho manual issue. Backend luôn set
`origin = MANUAL`; client không được gửi `origin`, `confidence`,
`validation_flags` hoặc ID/timestamp.

**Output — `201 Issue`:** `row_version = 1`.

**Lỗi chính:** `404 VERSION_NOT_FOUND`, `409 INVALID_STATE`,
`422 INVALID_ISSUE`.

### 8.3 GET `/projects/{project_id}/versions/{version_id}/issues/{issue_id}`

**Mục đích:** lấy issue cùng normalized source references.

**Input:** ba path IDs.

**Output — `200 Issue`.**

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`,
`404 ISSUE_NOT_FOUND`.

### 8.4 PATCH `/projects/{project_id}/versions/{version_id}/issues/{issue_id}`

**Mục đích:** autosave business fields mà không gửi lại toàn bộ resource.

**Input:**

```json
{
  "row_version": 3,
  "observed_gap": "Quarterly access review evidence was incomplete and not retained.",
  "evidence_summary": "One of four quarterly reviews was unavailable.",
  "risk_category": "Access Management",
  "source_refs": [
    {
      "ref_kind": "EVIDENCE",
      "document_id": "doc_01J5...",
      "unit_id": null,
      "location": {
        "sheet": "Access Review",
        "range": "A1:B12"
      },
      "quote": "Review completed by control owner"
    }
  ]
}
```

| Field | Required | Rule |
|---|---:|---|
| `row_version` | Có | Integer `>= 1` |
| Business field cần đổi | Có ít nhất một | `title_hint`, `observed_gap`, `evidence_summary`, `risk_category`, `source_refs` |
| `status` | Không | Dùng disposition API cho review decision |
| `origin`, `confidence`, `validation_flags` | Không được gửi | System/AI-owned |

**Output — `200 Issue`:** issue mới với `row_version + 1`.

**Lỗi chính:** `404 ISSUE_NOT_FOUND`, `409 ROW_VERSION_CONFLICT`,
`409 INVALID_STATE`, `422 INVALID_ISSUE`.

Nếu version đang có output `CURRENT`, edit issue giữ file cũ nhưng chuyển
output sang `STALE` và version sang `STALE_OUTPUT`.

### 8.5 POST `/projects/{project_id}/versions/{version_id}/issues/{issue_id}/disposition`

**Mục đích:** ghi quyết định review tách khỏi autosave nội dung.

**Input:**

```json
{
  "row_version": 4,
  "status": "APPROVED",
  "comment": "Evidence and criteria verified."
}
```

Status hợp lệ cho disposition:
`APPROVED | NEEDS_EVIDENCE | REJECTED | OUT_OF_SCOPE`.
`comment` optional trong UAT contract và được lưu vào audit trail.

**Output — `200 Issue`:** issue sau transition và row version mới.

**Lỗi chính:** `404 ISSUE_NOT_FOUND`, `409 ROW_VERSION_CONFLICT`,
`409 INVALID_STATE`, `422 INVALID_DISPOSITION`.

## 9. Discovery, Audit và job APIs

### 9.1 POST `/projects/{project_id}/versions/{version_id}/discovery-jobs`

**Mục đích:** enqueue AI discovery trên immutable source snapshot của project và
ghi candidates vào selected version. Discovery không tạo version mới.

**Headers:** `Idempotency-Key` required.

**Input:**

```json
{
  "force": false
}
```

`force = false` tái sử dụng result/job tương đương nếu có. `force = true`
chỉ được phép khi không có discovery active và phải tạo attempt có audit trail.

**Output — `202 Job`:** `job_type = DISCOVERY`, thường state `QUEUED`.

**Lỗi chính:** `404 VERSION_NOT_FOUND`, `409 ACTIVE_JOB_CONFLICT`,
`409 INVALID_STATE`, `422 SOURCE_NOT_READY`.

Runtime đã có durable orchestration, persistence và retry. AI engine được inject
qua application port; adapter mặc định chuyển job sang `FAILED` với error rõ
ràng cho tới khi đội AI cung cấp implementation. API vẫn trả `202 Job` để
frontend theo dõi trạng thái thống nhất.

### 9.2 POST `/projects/{project_id}/versions/{version_id}/audit-jobs`

**Mục đích:** preflight, freeze issue input snapshot và enqueue draft/validate/
render DOCX cho chính version hiện tại. Audit không tăng version.

**Headers:** `Idempotency-Key` required.

**Input:**

```json
{
  "issue_revision": 12
}
```

Preflight tối thiểu:

- request revision trùng current `issue_revision`;
- không có Audit active tương đương;
- issue được chọn cho output có `observed_gap`;
- AI candidate có evidence summary, `EVIDENCE` ref và `CRITERIA` ref;
- manual issue vẫn được phép thiếu refs theo UAT policy;
- central guideline/template version đang active.

**Output — `202 Job`:** `job_type = AUDIT`, state `QUEUED`.

**Lỗi chính:** `404 VERSION_NOT_FOUND`, `409 ACTIVE_JOB_CONFLICT`,
`409 INVALID_STATE`, `422 ISSUE_REVISION_STALE`,
`422 AUDIT_PREFLIGHT_FAILED`, `501 AI_PIPELINE_NOT_IMPLEMENTED`.

### 9.3 GET `/jobs/{job_id}`

**Mục đích:** phục hồi progress sau reload/reconnect.

**Input:** path `job_id`.

**Output — `200 Job`.**

**Lỗi chính:** `404 JOB_NOT_FOUND`.

### 9.4 GET `/jobs/{job_id}/events`

**Mục đích:** polling fallback khi SSE không dùng được.

**Input query:** `after_event_id` integer `>= 0`, default `0`.

**Output — `200 JobEvent[]`:** event có ID lớn hơn `after_event_id`, sort ASC.
Trả array rỗng khi chưa có event mới.

**Lỗi chính:** `404 JOB_NOT_FOUND`, `422 INVALID_EVENT_CURSOR`.

### 9.5 GET `/jobs/{job_id}/events/stream`

**Mục đích:** real-time progress bằng Server-Sent Events.

**Input:** query `after_event_id` hoặc header `Last-Event-ID`. Nếu cả hai có,
query được ưu tiên.

**Output — `200 text/event-stream`:**

```text
id: 17
event: progress
data: {"event_id":17,"job_id":"job_01J5...","stage":"PARSING","message":"Parsed 3 of 10 documents","completed_items":3,"total_items":10,"warning":false,"occurred_at":"2026-08-21T09:01:00Z"}

event: end
data: {}
```

Server gửi heartbeat comment định kỳ. `end` chỉ được gửi khi job terminal và
đã flush toàn bộ durable events.

**Lỗi trước khi mở stream:** `404 JOB_NOT_FOUND`.

### 9.6 POST `/jobs/{job_id}/retry`

**Mục đích:** retry job `FAILED` hoặc `INCOMPLETE` mà không tạo duplicate
output/version.

**Headers:** `Idempotency-Key` required.

**Input:**

```json
{
  "reason": "Retried after parser dependency recovered"
}
```

`reason` optional, tối đa 500 chars.

**Output — `202 Job`:** cùng logical job hoặc job kế nhiệm theo persistence
design, `attempt_count` tăng và state `QUEUED`.

**Lỗi chính:** `404 JOB_NOT_FOUND`, `409 JOB_NOT_RETRYABLE`,
`409 ACTIVE_JOB_CONFLICT`.

## 10. Output APIs

### 10.1 GET `/projects/{project_id}/versions/{version_id}/outputs`

**Mục đích:** list toàn bộ immutable output revisions của version.

**Input:** path `project_id`, `version_id`.

**Output — `200 OutputRevision[]`:** sort `ordinal DESC`; tối đa một revision
có status `CURRENT`.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`.

### 10.2 GET `/projects/{project_id}/versions/{version_id}/outputs/{output_id}/download`

**Mục đích:** download đúng DOCX thuộc project/version trong URL. Nested path
giúp authorization và audit log không dựa chỉ vào global `output_id`.

**Input:** path IDs; không có body.

**Output:**

- `200` stream DOCX với
  `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  và `Content-Disposition: attachment`; hoặc
- `302` tới short-lived signed URL của private object storage.

**Lỗi chính:** `404 PROJECT_NOT_FOUND`, `404 VERSION_NOT_FOUND`,
`404 OUTPUT_NOT_FOUND`, `410 OUTPUT_EXPIRED`,
`501 S3_STORAGE_NOT_CONFIGURED` trong runtime hiện tại.

## 11. API bridge hiện tại và kế hoạch migration

Frontend UAT hiện tại vẫn phụ thuộc nhóm route dưới đây. Không xoá chúng trong
thay đổi này vì sẽ làm hỏng browser flow đang chạy.

| Status | Method | Path | Input | Output hiện tại | Thay thế bởi |
|---|---|---|---|---|---|
| BRIDGE | `POST` | `/projects/upload` | `multipart/form-data`: `files[]`, `relative_paths[]`, optional `name` | `202 ProjectBridge`; tự chạy pipeline cũ | upload session + validate + promote + explicit jobs |
| BRIDGE | `GET` | `/projects` | none | `200 ProjectBridge[]` | target ProjectPage |
| BRIDGE | `GET` | `/projects/{project_id}` | path ID | `200 ProjectBridge` | target ProjectDetail |
| BRIDGE | `GET` | `/projects/{project_id}/events` | `after_event_id` | `200 ProjectEventBridge[]` | `/jobs/{job_id}/events` |
| BRIDGE | `GET` | `/projects/{project_id}/events/stream` | `after_event_id` | SSE progress | `/jobs/{job_id}/events/stream` |
| BRIDGE | `GET` | `/projects/{project_id}/output` | path ID | DOCX hoặc `409/410` | nested version output download |

Current `ProjectBridge` response:

```json
{
  "project_id": "project-id",
  "name": "Lumina Grand",
  "source_type": "LOCAL_FOLDER",
  "status": "PROCESSING",
  "current_activity": "Drafting issues",
  "allowed_actions": ["VIEW_STATUS", "VIEW_PROGRESS"],
  "created_at": "2026-08-21T08:00:00Z",
  "updated_at": "2026-08-21T08:01:00Z",
  "started_at": "2026-08-21T08:00:10Z",
  "completed_at": null,
  "output_available": false,
  "output_download_url": null,
  "version": null,
  "issue_count": null,
  "error": null,
  "raw_expires_at": "2026-08-28T08:00:00Z",
  "raw_deleted_at": null
}
```

Bridge retirement conditions:

1. frontend tích hợp upload-session local flow và bỏ bridge upload;
2. promote tạo project + `v0.1`;
3. frontend chuyển sang explicit discovery/Audit jobs;
4. frontend tải output theo project/version/output ID;
5. UAT regression cho upload → review → Audit → download pass.

### 11.1 Runtime-only endpoints đang chờ migration

Hai path dưới đây vẫn xuất hiện trong OpenAPI runtime nhưng không thuộc
contract đích:

| Method | Path | Input hiện tại | Output hiện tại | Migration |
|---|---|---|---|---|
| `PUT` | `/projects/{project_id}/versions/{version_id}/issues/{issue_id}` | Full payload gồm `row_version`, `observed_gap`, `title_hint`, `evidence_summary`, `risk_category`, `status`, `confidence`, `validation_flags`, `source_refs` | `200 Issue` | Thay bằng partial `PATCH`; system-owned fields không cho client ghi |
| `GET` | `/outputs/{output_id}/download` | Path `output_id` | Hiện trả `501 S3_STORAGE_NOT_CONFIGURED` | Thay bằng nested project/version/output path |

Payload đầy đủ của `PUT issue` hiện tại:

```json
{
  "row_version": 3,
  "observed_gap": "Quarterly access review evidence was incomplete.",
  "title_hint": "Access review evidence retention",
  "evidence_summary": "One of four quarterly reviews was unavailable.",
  "risk_category": "Access Management",
  "status": "READY_FOR_REVIEW",
  "confidence": 0.86,
  "validation_flags": [],
  "source_refs": []
}
```

Không build client mới dựa trên hai endpoint này. Chỉ remove sau khi frontend
đã chuyển sang `PATCH` và nested output download.

### 11.2 API POC đã xoá

Nhóm `/api/v1/runs*` nhận local server paths, không được frontend UAT gọi và
đã được gỡ khỏi router/OpenAPI:

- `POST /runs`;
- `GET /runs`;
- `GET /runs/{run_id}`;
- `GET /runs/{run_id}/events`;
- `GET /runs/{run_id}/events/stream`;
- `GET /runs/{run_id}/output`.

CLI `python backend/main.py --project ... --issues ...` là tool nội bộ riêng,
không phải public HTTP contract và vẫn được giữ.

## 12. Runtime gaps cần đóng trước UAT sign-off

| Gap | Runtime hiện tại | Contract đích |
|---|---|---|
| Upload storage | Local adapter chạy end-to-end | Thêm S3 adapter, giữ nguyên service contract |
| Project list/detail | Trả `ProjectBridge` | ProjectPage/ProjectDetail |
| Issue list | Trả array | IssuePage có cursor |
| Issue update | `PUT`, full editable payload | `PATCH`, partial business fields |
| Disposition comment | Chưa có | Optional `comment` và audit trail |
| Discovery | Durable `202 Job`; adapter mặc định fail có kiểm soát khi AI chưa cấu hình | Inject AI engine production |
| Audit | Route trả `501 AI_PIPELINE_NOT_IMPLEMENTED` | Durable `202 Job` |
| Retry | `202` cho `FAILED`/`INCOMPLETE`, lưu retry reason | Bổ sung idempotency-key persistence |
| Output download | Global `/outputs/{output_id}/download`, trả `501` | Nested project/version path |
| Idempotency | Chưa enforce đồng đều | Required cho command endpoint |
| UAT limits | Đã enforce 20 files và 100,000,000 bytes | Giữ cấu hình tương đương trên S3 |

Không coi route `501` là feature đã hoàn thành. Swagger chỉ chứng minh contract
đã publish, không chứng minh luồng UAT end-to-end đã sẵn sàng.

## 13. Mã lỗi nghiệp vụ

| HTTP | Code | Khi nào |
|---:|---|---|
| 404 | `UPLOAD_SESSION_NOT_FOUND` | Không tìm thấy upload session |
| 404 | `PROJECT_NOT_FOUND` | Không tìm thấy project |
| 404 | `VERSION_NOT_FOUND` | Không tìm thấy version trong project |
| 404 | `ISSUE_NOT_FOUND` | Không tìm thấy issue trong version |
| 404 | `JOB_NOT_FOUND` | Không tìm thấy job |
| 404 | `OUTPUT_NOT_FOUND` | Không tìm thấy output trong version |
| 409 | `DUPLICATE_PROJECT_NAME` | Tên project đã tồn tại |
| 409 | `ROW_VERSION_CONFLICT` | Issue update dùng row version cũ |
| 409 | `ACTIVE_JOB_CONFLICT` | Job tương đương đang queued/running |
| 409 | `INVALID_STATE` | Workflow transition không hợp lệ |
| 409 | `JOB_NOT_RETRYABLE` | Retry job chưa terminal hoặc đã succeeded |
| 409 | `SESSION_ALREADY_PROMOTED` | Upload session đã tạo project |
| 410 | `UPLOAD_SESSION_EXPIRED` | Staging hết retention |
| 410 | `OUTPUT_EXPIRED` | Output không còn trong retention |
| 413 | `FOLDER_TOO_LARGE` | Tổng content length vượt 100 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | Không phải DOCX/PDF/XLSX |
| 422 | `INVALID_UPLOAD_MANIFEST` | Path/metadata/file count không hợp lệ |
| 422 | `SESSION_NOT_READY` | Promote trước khi validation pass |
| 422 | `INVALID_ISSUE` | Issue business fields không hợp lệ |
| 422 | `INVALID_DISPOSITION` | Review status/transition không hợp lệ |
| 422 | `ISSUE_REVISION_STALE` | Audit submit bằng revision cũ |
| 422 | `AUDIT_PREFLIGHT_FAILED` | Issue/source/asset chưa đủ để Audit |
| 501 | `S3_STORAGE_NOT_CONFIGURED` | Capability cần object storage chưa sẵn sàng |
| 501 | `AI_PIPELINE_NOT_IMPLEMENTED` | Discovery/Audit worker chưa implement |
