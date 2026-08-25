# Trạng thái Frontend

> Xác minh gần nhất: 04/08/2026
> Trạng thái bàn giao: POC đã triển khai
> Source of truth: `frontend/src/`

## Kết quả hiện tại

Vue app đã hỗ trợ đầy đủ happy path của POC: chọn local audit folder, nhập hoặc
import auditor inputs, review trước khi chạy, theo dõi xử lý và tải DOCX. App
chạy qua Nginx trong Docker Compose, dùng logo CDL và giao diện sáng với màu
nhấn cam/đen.

```text
Project & artefacts
  → Nhập tay/import auditor inputs
  → Review & upload
  → Live processing → Completed/Failed → Download
```

## UAT v2 UI refresh (24/08/2026)

Frontend đã có information architecture **2 route + modal** theo bộ thiết kế
`frontend/design/uat-v2/`:

- `/projects`: dashboard dạng bảng, status theo workflow v2 và mở Project Detail.
- `/projects/:projectId`: shared project/version header và ba tab
  `Source & discovery`, `Candidate issues`, `Runs & outputs`.
- New Project dùng hai bước staging upload -> server validation -> promote project;
  không còn auditor JSON trong happy path và không tự chạy discovery.
- `Source & discovery` chỉ hiện progress sau khi bấm **Find candidates**; lỗi
  `INCOMPLETE` thay CTA bằng **View error / Retry**.
- Candidate Register dùng body hai cột; Audit confirmation giữ frozen snapshot.
- Runs & outputs giữ output revision cũ và cho tải theo từng revision.

Các component dùng chung nằm trong `frontend/src/modules/projects/`, gồm
`WorkspaceHeader`, `ProjectDetailHeader`, ba tab body và các modal độc lập.
API discovery/Audit hiện vẫn trả `501 AI_PIPELINE_NOT_IMPLEMENTED`; UI đã hiển thị
lỗi/retry theo contract, không giả lập job thành công.

Baseline sau thay đổi: typecheck pass, 8 unit tests pass và production build pass.

## Checklist chức năng

| Chức năng | Trạng thái | Bằng chứng trong source |
|---|---|---|
| Projects workspace | Đã xong | `frontend/src/modules/projects/ProjectsWorkspace.vue` |
| Logo công ty và theme | Đã xong | `frontend/src/assets/cdl-logo.png`, `styles.css` |
| Responsive desktop/mobile | Đã xong | `frontend/src/assets/styles.css` |
| Chọn local folder | Đã xong | `webkitdirectory` trong `ProjectSetupWizard.vue` |
| Nhập tay nhiều auditor issues | Đã xong | Issue navigator và editor trong setup wizard |
| Import/validate JSON | Đã xong | `shared/auditor-inputs.ts` |
| Lọc source artefacts cho reference | Đã xong | Chỉ hiện `.docx/.pdf/.xlsx` trong sáu folder backend parse; loại hidden, `Output` và generated files |
| Review trước khi chạy | Đã xong | Bước `Review & run` trong setup wizard |
| Multipart upload giữ relative path | Đã xong | `frontend/src/shared/api/projects.ts` |
| Browser upload progress | Đã xong | `XMLHttpRequest.upload` progress |
| Project list và detail | Đã xong | Projects workspace |
| Live progress timeline | Đã xong | Native `EventSource` |
| Khôi phục kết nối SSE | Đã xong | Refresh snapshot và reconnect từ event ID cuối |
| API error và correlation ID | Đã xong | `ApiClientError` và error banner |
| Download DOCX | Đã xong | Theo backend action `DOWNLOAD_OUTPUT` |
| Browser E2E trong repository | Chưa làm | Mới có Playwright smoke check tạm thời |
| Auditor input review UI | Đã xong | Review các seed issues trước khi gọi drafting pipeline |
| Authentication UI | Chưa làm | Phụ thuộc backend identity design |

## Bố cục UI

POC cố ý giữ một workspace duy nhất:

1. Header có logo CDL và trạng thái kết nối.
2. Summary cards theo trạng thái project.
3. Project list bên trái.
4. Status và activity của project được chọn bên phải.
5. Setup wizard ba bước: Project & Artefacts → Auditor Inputs → Review & Run.

POC có review gate cho auditor-provided seed issues, nhưng chưa có AI discovery,
Candidate Issue Register hoặc review draft sau khi AI sinh.

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
| `npm test` | 8 tests pass |
| `npm run build` | Pass |
| Production JS bundle | 104.25 kB, 38.28 kB gzip |
| Production CSS bundle | 31.88 kB, 7.25 kB gzip |
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
