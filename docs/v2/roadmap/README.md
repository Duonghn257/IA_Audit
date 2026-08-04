# Delivery Roadmap

> Review gần nhất: 03/08/2026
> Nguyên tắc: Chốt POC trước; stabilization, production và product v2 làm sau

Đây là nơi duy nhất ghi planned work. Các trang `status/` mô tả những gì đang
tồn tại; `reference/` mô tả thiết kế dài hạn.

Quy ước trạng thái:

- `NEXT`: nên làm ngay.
- `PLANNED`: đã thống nhất hướng, chưa bắt đầu.
- `DEFERRED`: chủ động để ngoài scope hiện tại.
- `DONE`: đã xác minh acceptance criteria và cập nhật status page liên quan.

## Mục tiêu release hiện tại

Có một POC demo ổn định: auditor upload Lumina Grand từ browser, theo dõi đến
terminal state và tải được DOCX sử dụng được.

## Next — chốt POC

| ID | Work item | Trạng thái | Dependency |
|---|---|---|---|
| POC-01 | Browser E2E với `data/lumina_grand` | `NEXT` | LLM endpoint và root `sample_issues.json` hợp lệ |
| POC-02 | Auditor UAT generated DOCX | `NEXT` | POC-01 |
| POC-03 | Check in Playwright happy-path test | `NEXT` | POC-01 flow ổn định |
| POC-04 | Test frontend API error và SSE reconnect | `NEXT` | Vitest setup hiện tại |
| POC-05 | Bảo vệ demo credentials và HTTPS routing | `NEXT` | Quyết định demo environment |

### POC-01 — Real browser run

Acceptance criteria:

- Chọn full `data/lumina_grand` trong Vue upload dialog.
- Upload xong, không lỗi path/count/size validation.
- Timeline nhận ordered SSE events và phục hồi sau một lần forced reconnect.
- Project đạt `COMPLETED`; nếu fail phải lưu useful error và correlation ID.
- Downloaded file mở được như DOCX hợp lệ.
- Project/event history còn tồn tại sau container restart.

### POC-02 — Auditor acceptance

Acceptance criteria:

- Auditor xác nhận report structure và branding dùng được cho demo.
- Draft content map được về `sample_issues.json` và project evidence.
- Content defects được lưu thành reproducible fixtures hoặc test cases.
- Demo limitations được ghi nhận rõ.

### POC-03 — Browser regression test

Acceptance criteria:

- Playwright test được lưu trong repository và có một lệnh chạy được document.
- Cover empty state, folder validation, upload, processing, completion và
  download bằng deterministic/fake backend khi phù hợp.
- CI hoặc local verification sequence chính thức chạy test này.

### POC-04 — Frontend resilience tests

Acceptance criteria:

- Test structured và non-JSON API errors.
- Test correlation-ID display.
- Test missed-event recovery và deduplication sau SSE reconnect.
- Test action rendering ở `FAILED` và `COMPLETED`.

### POC-05 — Demo deployment safety

Acceptance criteria:

- Thay default PostgreSQL password.
- LLM credentials nằm ngoài Git và không xuất hiện trong logs.
- Có HTTPS phía trước app nếu expose ngoài localhost.
- Chỉ các ports cần thiết được truy cập.
- Có hướng dẫn ngắn backup/recovery cho demo data.

## Planned — ổn định implementation

| ID | Work item | Trạng thái | Lý do |
|---|---|---|---|
| STAB-01 | Startup recovery cho stranded projects | `PLANNED` | API restart có thể để `PROCESSING` mãi |
| STAB-02 | Retry/cancel project operations | `PLANNED` | Job fail hiện phải upload project mới |
| STAB-03 | Durable stage checkpoints và idempotency | `PLANNED` | Tránh chạy lại toàn bộ LLM pipeline |
| STAB-04 | Upload MIME allowlist và malware scanning | `PLANNED` | Rủi ro từ untrusted binary uploads |
| STAB-05 | Scheduled raw-input retention | `PLANNED` | Cleanup hiện chỉ chạy lúc startup |
| STAB-06 | Project pagination/filtering | `PLANNED` | Project list hiện chỉ phù hợp POC scale |
| STAB-07 | Bỏ production `create_all()` path | `PLANNED` | Alembic phải là schema authority |

Một stabilization item chỉ hoàn thành khi implementation, automated tests và
status page liên quan được cập nhật cùng nhau.

## Planned — production foundation

| ID | Work item | Trạng thái |
|---|---|---|
| PROD-01 | Entra ID authentication và project authorization | `PLANNED` |
| PROD-02 | Durable queue/worker, retry và dead-letter policy | `PLANNED` |
| PROD-03 | Encrypted object storage adapter | `PLANNED` |
| PROD-04 | SharePoint folder source và output publishing | `PLANNED` |
| PROD-05 | Secrets manager/workload identity | `PLANNED` |
| PROD-06 | Structured logging, metrics, tracing và alerts | `PLANNED` |
| PROD-07 | PostgreSQL/object backup và restore procedures | `PLANNED` |
| PROD-08 | Multi-instance-safe events/outbox | `PLANNED` |

Các items này cần architecture và security decisions trước khi implement. Xem
[Target Architecture](../reference/TARGET_ARCHITECTURE.md) và
[Source Architecture](../reference/SOURCE_ARCHITECTURE.md).

## Deferred — product v2

Các chức năng dưới đây có giá trị nhưng không được chặn POC hiện tại:

- Evidence-driven candidate issue discovery.
- Coverage Matrix và incomplete-evidence handling.
- Observation Inbox.
- Draft Issue Review.
- Auditor approve/edit/merge/split/reject actions.
- Approval gates trước DOCX rendering.
- Output history và SharePoint publishing.
- Bedrock provider adapter.

Chỉ chuyển item ra khỏi `DEFERRED` sau khi thống nhất product flow, data
contract, security boundary và acceptance criteria.

## Quy tắc cập nhật

Khi một work item đổi trạng thái:

1. Cập nhật trạng thái tại đây.
2. Ghi behavior và test results đã xác minh vào status page liên quan.
3. Chỉ cập nhật reference architecture nếu design decision thay đổi.
4. Không copy cùng một progress narrative sang nhiều file.
