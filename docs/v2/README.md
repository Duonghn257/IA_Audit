# Operation Report Jedi — Delivery Hub

> Cập nhật: 10/08/2026
> Trạng thái tổng thể: POC end-to-end đã chạy; đang chốt browser E2E và UAT

Đây là điểm bắt đầu để xem project đang ở đâu và nên làm gì tiếp theo. Tài liệu
được tách thành trạng thái hiện tại, roadmap, SRS UAT và kiến trúc tham khảo.

## Trạng thái nhanh

| Khu vực | Hiện tại | Chi tiết |
|---|---|---|
| Frontend | Vue Projects workspace đã triển khai | [Frontend Status](status/FRONTEND.md) |
| Backend | FastAPI project API và pipeline 8 bước đã triển khai | [Backend Status](status/BACKEND.md) |
| Database | PostgreSQL 16 + Alembic revision `20260729_01` | [Infrastructure Status](status/INFRASTRUCTURE.md) |
| Runtime | PostgreSQL, backend và frontend/Nginx chạy bằng Compose | [Infrastructure Status](status/INFRASTRUCTURE.md) |
| Live progress | Persistent events + SSE reconnect | [Frontend](status/FRONTEND.md) / [Backend](status/BACKEND.md) |
| Output | Backend render và frontend download DOCX | [Backend Status](status/BACKEND.md) |
| POC còn thiếu | Browser Lumina E2E, auditor UAT, browser regression tests | [Delivery Roadmap](roadmap/README.md) |
| Production | Auth, durable worker, object storage, SharePoint chưa làm | [Delivery Roadmap](roadmap/README.md) |

## Việc cần làm ngay

1. Chạy toàn bộ `data/lumina_grand` qua browser đến khi tải được DOCX.
2. Cho auditor đánh giá output và ghi lại các lỗi có thể tái hiện.
3. Check in Playwright E2E và bổ sung test lỗi API/SSE reconnect.
4. Chuẩn bị credential, HTTPS và giới hạn network cho môi trường demo.

Acceptance criteria và thứ tự dependency nằm tại
[Delivery Roadmap](roadmap/README.md).

Baseline yêu cầu mới cho luồng UAT local upload → background discovery → issue
review → background Audit → versioned DOCX nằm tại
[Software Requirements Specification](SOFTWARE_REQUIREMENTS_SPECIFICATION.md).
Estimation, staffing assumptions, milestones và critical dependencies cho
release 15/09/2026 nằm tại [UAT Release Estimation Plan](UAT_ESTIMATION_PLAN.md).
Checklist triển khai riêng cho Backend/AI, bao gồm thứ tự dependency và effort
còn lại, nằm tại
[Backend and AI UAT Implementation Checklist](BACKEND_AI_IMPLEMENTATION_CHECKLIST.md).
Danh sách AWS services, roles và IAM permissions để xin UAT environment nằm tại
[AWS UAT Access Request](AWS_UAT_ACCESS_REQUEST.md).

## Cấu trúc tài liệu

```text
docs/v2/
├── README.md
├── SOFTWARE_REQUIREMENTS_SPECIFICATION.md
├── UAT_ESTIMATION_PLAN.md
├── BACKEND_AI_IMPLEMENTATION_CHECKLIST.md
├── AWS_UAT_ACCESS_REQUEST.md
├── status/
│   ├── FRONTEND.md
│   ├── BACKEND.md
│   └── INFRASTRUCTURE.md
├── roadmap/
│   └── README.md
├── reference/
│   ├── TARGET_ARCHITECTURE.md
│   └── SOURCE_ARCHITECTURE.md
└── diagrams/
    └── frontend-wireframes.svg
```

### `status/` — những gì đang tồn tại

Dùng khi cần trả lời:

- Chức năng nào đã chạy?
- Source nằm ở đâu?
- Đã kiểm tra bằng lệnh nào?
- Giới hạn thực tế hiện tại là gì?

Các trang status phải mô tả code/runtime đã được xác minh, không mô tả giải
pháp tương lai như thể đã triển khai.

### `roadmap/` — những gì sẽ làm

Dùng để quản lý `NEXT`, `PLANNED`, `DEFERRED`, dependency và acceptance
criteria. Đây là nơi duy nhất ghi danh sách công việc tương lai.

### `reference/` — thiết kế dài hạn

Dùng để giải thích target architecture, boundaries và design patterns. Các file
này không phải báo cáo tiến độ và không nên được đọc trước status/roadmap.

### `SOFTWARE_REQUIREMENTS_SPECIFICATION.md` — baseline UAT

Dùng để quản lý requirement ID, acceptance criteria, release `UAT-R1..R4` và
project version semantics. SRS mô tả target cần nghiệm thu, không phải trạng thái
đã triển khai.

### `UAT_ESTIMATION_PLAN.md` — kế hoạch release

Dùng để theo dõi person-day estimate, staffing assumptions, delivery dates,
release gates và dependency cho deadline 15/09/2026.

## Baseline đã xác minh

| Kiểm tra | Kết quả |
|---|---|
| Backend tests | 14 passed, 1 deprecation warning |
| Frontend typecheck | Pass |
| Frontend tests | 2 passed |
| Frontend production build | Pass |
| Docker Compose config | Pass |
| PostgreSQL/backend/frontend health | Healthy |
| Health qua Nginx | HTTP 200 |
| Alembic | `20260729_01 (head)`, không có schema drift |
| Lumina Grand qua compatibility CLI | Hoàn thành 8/8 stages, DOCX hợp lệ |
| Lumina Grand qua browser | Chưa xác minh end-to-end |

## Cách cập nhật tiến độ

Khi hoàn thành một thay đổi:

1. Cập nhật đúng một trang trong `status/` với behavior và test evidence.
2. Đổi trạng thái work item tương ứng trong `roadmap/README.md`.
3. Chỉ sửa `reference/` nếu quyết định kiến trúc thay đổi.
4. Không sao chép cùng một progress log sang nhiều file.
5. Ghi ngày `Last verified` sau khi đã chạy lại verification liên quan.

Thứ tự ưu tiên khi thông tin mâu thuẫn:

```text
code + automated tests + running Compose
  → status/
  → roadmap/
  → reference/
  → tài liệu lịch sử ngoài docs/v2
```

Hướng dẫn cài đặt và chạy project nằm ở [root README](../../README.md).
