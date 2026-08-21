# Operation Report Jedi — Kế hoạch delivery FE, BE và AI

> **Cập nhật:** 21/08/2026
> **Trạng thái:** Baseline phân công và delivery cho UAT
> **Mốc delivery:** UAT lần đầu ngày **11/09/2026**; release chính thức ngày **17/09/2026**.
> **Kiến trúc đích:** [Target Architecture](reference/TARGET_ARCHITECTURE.md).
> **Yêu cầu phần mềm:** [Software Requirements Specification](SOFTWARE_REQUIREMENTS_SPECIFICATION.md).

Tài liệu này phân chia công việc theo ba role FE, BE và AI ở mức outcome,
dependency và milestone. Dev tự breakdown thành task kỹ thuật trong từng luồng.

## 1. Nguyên tắc lập kế hoạch

Kế hoạch tính từ ngày 24/08/2026, với hai mốc bắt buộc:

- **11/09/2026 — UAT lần đầu:** có một vertical slice deploy được để auditor
  chạy toàn bộ luồng từ local folder đến versioned DOCX.
- **17/09/2026 — Release chính thức:** xử lý xong lỗi release-blocking từ UAT,
  hoàn tất regression, vận hành và bàn giao.

Ba role FE, BE và AI có owner riêng và làm song song trên contract đã thống
nhất. Kế hoạch chỉ khả thi khi cả ba luồng có bandwidth thực tế tương đương ba
owner; nếu một người phải kiêm BE và AI, PM phải bổ sung capacity hoặc giảm
scope trước ngày 28/08. Không có QA riêng; mỗi role chịu trách nhiệm test phần
mình và tham gia cross-test E2E. Từ ngày 07/09, team không nhận thêm scope mới;
chỉ hoàn thiện vertical slice, sửa lỗi và hardening.

## 2. Phân công theo role

| Role | Trách nhiệm delivery | Kết quả phải bàn giao |
|---|---|---|
| **FE** | Xây workflow upload/create project, project/version workspace, live progress, Candidate Issue Register, manual issue, review/disposition, Audit và download | Auditor hoàn thành được happy path và hiểu rõ loading, empty, warning, failed, retry, stale và version states |
| **BE** | Chốt API/data model; quản lý staging và immutable source; background jobs, event/retry; issue/version APIs; frozen Audit input; output revisions, download, deployment và audit trail | API và persistence hỗ trợ đầy đủ lifecycle, job chạy bền vững, không tạo trùng version/output và có thể phục hồi sau restart |
| **AI** | Parse có provenance; lập scope/control map; trích xuất evidence/criteria; candidate discovery, coverage và validation; draft accepted issues và kiểm tra output | Mọi AI candidate truy được về Evidence + Criteria, draft không tự thêm issue và kết quả được kiểm chứng trên golden UAT dataset |

Ranh giới ownership không loại bỏ phối hợp: BE cung cấp contract và job
orchestration cho FE/AI; AI cung cấp schema, trạng thái và validation result cho
BE/FE; FE xác nhận contract có thể sử dụng được qua browser workflow.

## 3. Kế hoạch theo thời gian

| Thời gian | FE | BE | AI | Milestone chung |
|---|---|---|---|---|
| **24–28/08** | Hoàn thiện intake flow, folder tree/validation và project workspace theo API contract | Chốt domain/API schema; migration; staging, server validation, immutable source và tạo `v0.1`; dựng nền durable job | Chốt AI schemas và golden dataset; hoàn thiện parsing/provenance, scope, criteria và evidence contracts | Contract freeze và một project hợp lệ được tạo thành `v0.1` mà chưa tự chạy discovery |
| **31/08–04/09** | Hoàn thiện progress/reconnect, Candidate Register, detail/edit/disposition và manual issue | Hoàn thiện worker, progress/retry/recovery, discovery integration, issue APIs và **+ New audit** | Hoàn thiện discovery từ scope/control đến candidates, deduplication, Coverage Matrix và blocking validation | Vertical slice discovery chạy được; auditor xem và quyết định candidate trên portal |
| **07–10/09** | Hoàn thiện version navigation, Audit, stale/output/download states; browser E2E và sửa lỗi tích hợp | Đóng băng Audit input, tạo output revision, versioned download, idempotency và deploy UAT | Hoàn thiện drafting/final validation/DOCX; tune trên golden dataset và kiểm tra citation | Release Candidate 1 chạy trọn `upload → discovery → review → Audit → download` |
| **11/09** | Smoke test UI và hỗ trợ auditor | Deploy, migration check, giám sát job/API và hỗ trợ UAT | Kiểm tra AI run manifest, citations và chất lượng output | **UAT lần đầu**; ghi nhận defect có severity, owner và cách tái hiện |
| **14–16/09** | Sửa lỗi UAT, regression các browser states | Sửa lỗi UAT, hardening, backup/rollback và release candidate cuối | Sửa lỗi chất lượng/citation có thể tái hiện; khóa prompt/model/schema versions | Chỉ xử lý P0/P1 và regression; go/no-go review cuối ngày 16/09 |
| **17/09** | Production smoke test và handover | Deploy chính thức, migration/smoke test và theo dõi sau release | Xác minh một production run kiểm soát và output | **Release chính thức** |

## 4. Dependencies và điểm bàn giao bắt buộc

| Hạn | Dependency / quyết định | Owner chính | Ảnh hưởng nếu trễ |
|---|---|---|---|
| **26/08** | API contract, state machine và AI output schemas được freeze | BE + AI | FE không thể tích hợp ổn định; test E2E bị dồn |
| **28/08** | Golden UAT dataset, central Guidelines và DOCX template được business xác nhận | PM/Business + AI | Không có baseline để đánh giá candidate và output |
| **04/09** | UAT environment, database, object storage, secrets, HTTPS và network access sẵn sàng | BE/Infrastructure | Không đủ thời gian kiểm tra restart, download và deployment |
| **08/09** | Integrated build deploy được và có dữ liệu test | FE + BE + AI | Mốc UAT 11/09 có rủi ro cao |
| **11–16/09** | Auditor/Product Owner có lịch test và phản hồi theo severity trong ngày | PM/Business | Không đủ thời gian xác nhận fix trước release |

PM duy trì một backlog chung theo outcome và severity. Dev tự breakdown kỹ
thuật trong từng role; kế hoạch này không dùng để micro-manage implementation.

## 5. Release gates

**Gate UAT ngày 11/09**

- Một golden project chạy trọn luồng browser từ upload đến tải đúng DOCX.
- Project tạo đúng `v0.1`; **+ New audit** và Audit tuân đúng version semantics.
- Mỗi AI candidate có Evidence và Criteria refs mở được; manual issue giữ đúng
  `origin = MANUAL`.
- Discovery và Audit chạy background, UI nhận progress thật và phục hồi sau
  reload/reconnect.
- Không có P0; mọi P1 còn lại có owner, workaround và kế hoạch đóng trước 16/09.
- Các giới hạn đã biết được ghi rõ cho auditor.

**Gate release ngày 17/09**

- Không còn P0/P1 mở; các UAT acceptance scenarios và regression đều pass.
- Retry không tạo duplicate version hoặc output; re-Audit không mất output cũ.
- Internal access, secrets, retention, download protection, logging redaction,
  backup và rollback đã được kiểm tra.
- Model, prompt, parser, schema, central assets và release image đều được khóa
  version và xuất hiện trong run manifest.
- Go/no-go được PM, Tech Lead và Product Owner xác nhận.

