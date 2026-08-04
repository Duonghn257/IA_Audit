# Trạng thái Frontend

> Xác minh gần nhất: 03/08/2026
> Trạng thái bàn giao: POC đã triển khai
> Source of truth: `frontend/src/`

## Kết quả hiện tại

Vue app đã hỗ trợ đầy đủ happy path của POC: chọn local audit folder, theo dõi
xử lý và tải DOCX. App chạy qua Nginx trong Docker Compose, dùng logo CDL và
giao diện sáng với màu nhấn cam/đen.

```text
Chọn folder → Validate → Upload → Live processing → Completed/Failed → Download
```

## Checklist chức năng

| Chức năng | Trạng thái | Bằng chứng trong source |
|---|---|---|
| Projects workspace | Đã xong | `frontend/src/modules/projects/ProjectsWorkspace.vue` |
| Logo công ty và theme | Đã xong | `frontend/src/assets/cdl-logo.png`, `styles.css` |
| Responsive desktop/mobile | Đã xong | `frontend/src/assets/styles.css` |
| Chọn local folder | Đã xong | `webkitdirectory` trong `UploadProjectDialog.vue` |
| Validate `sample_issues.json` ở root | Đã xong | `hasRootIssuesFile` trong upload dialog |
| Multipart upload giữ relative path | Đã xong | `frontend/src/shared/api/projects.ts` |
| Browser upload progress | Đã xong | `XMLHttpRequest.upload` progress |
| Project list và detail | Đã xong | Projects workspace |
| Live progress timeline | Đã xong | Native `EventSource` |
| Khôi phục kết nối SSE | Đã xong | Refresh snapshot và reconnect từ event ID cuối |
| API error và correlation ID | Đã xong | `ApiClientError` và error banner |
| Download DOCX | Đã xong | Theo backend action `DOWNLOAD_OUTPUT` |
| Browser E2E trong repository | Chưa làm | Mới có Playwright smoke check tạm thời |
| Observation/Issue Review UI | Deferred | Ngoài POC hiện tại |
| Authentication UI | Chưa làm | Phụ thuộc backend identity design |

## Bố cục UI

POC cố ý giữ một workspace duy nhất:

1. Header có logo CDL và trạng thái kết nối.
2. Summary cards theo trạng thái project.
3. Project list bên trái.
4. Status và activity của project được chọn bên phải.
5. Upload dialog để chọn folder và đặt tên project.

POC không có Observation Inbox, Draft Issue Review hoặc approval gates. Đây là
các flow của target product sau POC.

Design reference: [frontend wireframes](../diagrams/frontend-wireframes.svg).

## Backend contract frontend đang dùng

```text
POST /api/v1/projects/upload
GET  /api/v1/projects
GET  /api/v1/projects/{project_id}
GET  /api/v1/projects/{project_id}/events
GET  /api/v1/projects/{project_id}/events/stream
GET  /api/v1/projects/{project_id}/output
```

Quy tắc frontend:

- Mỗi part `files` phải có đúng một form value `relative_paths` tương ứng.
- Không gửi hoặc hiển thị absolute path từ máy auditor.
- Render action theo `allowed_actions` do backend trả về.
- SSE disconnect là lỗi kết nối, không phải project `FAILED`.
- Chỉ hiển thị `output_download_url` khi project hoàn thành.

Swagger có thể hiển thị binary file thành chuỗi ký tự lạ do cách Swagger UI
render file array của OpenAPI 3.1. Vue client vẫn gửi đúng multipart body; đây
không phải lỗi hỏng file.

## Baseline kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| `npm run typecheck` | Pass |
| `npm test` | 2 tests pass |
| `npm run build` | Pass |
| Production JS bundle | 87.76 kB, 33.87 kB gzip |
| Production CSS bundle | 20.38 kB, 5.32 kB gzip |
| Frontend container health | Healthy |
| API health qua Nginx | HTTP 200 |
| Playwright smoke tạm thời | Page load, dialog và folder selection pass |

Chạy lại kiểm thử:

```bash
cd frontend
npm run typecheck
npm test
npm run build
```

## Giới hạn hiện tại

- Chưa upload full `data/lumina_grand` qua browser đến output cuối.
- Automated tests chưa cover API failure và SSE reconnect.
- Chưa có retry, cancel, search, filter hoặc pagination.
- Folder picker phụ thuộc browser support cho `webkitdirectory`.
- Upload progress chỉ đo browser → server; pipeline progress bắt đầu sau khi
  multipart request được backend nhận xong.

## Khi nào cập nhật file này

Cập nhật khi behavior, màn hình, dependency, test hoặc giới hạn frontend thay
đổi. Công việc tương lai ghi tại [roadmap](../roadmap/README.md); design dài hạn
ghi tại [source architecture](../reference/SOURCE_ARCHITECTURE.md).
