# Software Requirements Specification — UAT

> **Sản phẩm:** Operation Report Jedi — AI-assisted Audit Issue Discovery and Drafting
>
> **Phiên bản tài liệu:** SRS 0.4
>
> **Ngày:** 10/08/2026
>
> **Trạng thái:** Final UAT scope baseline; implementation dependencies tracked separately
>
> **Phạm vi:** UAT web application dùng folder upload từ máy người dùng

## 1. Kiểm soát tài liệu

### 1.1 Lịch sử thay đổi

| Phiên bản SRS | Ngày | Nội dung |
|---|---|---|
| `0.1` | 10/08/2026 | Baseline yêu cầu cho local upload, candidate discovery, manual issues, background audit, DOCX download và project version history |
| `0.2` | 10/08/2026 | Chốt central Guidelines/template, AI-vs-manual evidence policy, optional risk, format/100 MB limit, manual AI review, Entra target; defer Merge/Split và Cancel |
| `0.3` | 10/08/2026 | Chốt tối đa 20 files/folder và version lifecycle: upload tạo `v0.1`, **+ New audit** tạo `v0.2+`, Audit gắn DOCX vào current version |
| `0.4` | 10/08/2026 | Thu gọn internal UAT: không có app login/RBAC; Entra, Bedrock, Textract và SQS deferred; worker dùng durable jobs trong PostgreSQL |

Phiên bản SRS là phiên bản của tài liệu yêu cầu. Nó không phải phiên bản nội
dung của một audit project (`v0.1`, `v0.2`, ...), cũng không phải release của
phần mềm (`UAT-R1`, `UAT-R2`, ...).

### 1.2 Tài liệu liên quan

- [Target Architecture](reference/TARGET_ARCHITECTURE.md)
- [Source Architecture](reference/SOURCE_ARCHITECTURE.md)
- [Delivery Roadmap](roadmap/README.md)
- [Current Frontend Status](status/FRONTEND.md)
- [Current Backend Status](status/BACKEND.md)

### 1.3 Quy ước từ khóa

- **MUST / phải:** bắt buộc để nghiệm thu release.
- **SHOULD / nên:** mặc định phải làm; chỉ bỏ khi có quyết định được ghi lại.
- **MAY / có thể:** tùy chọn, không chặn nghiệm thu.

## 2. Mục tiêu sản phẩm

Ứng dụng cho phép auditor:

1. Upload một folder audit project từ máy cá nhân và xác nhận bộ artefacts hợp lệ.
2. Tạo project có source snapshot bất biến.
3. Chủ động bấm **Find candidates** để AI tìm candidate issues trong background.
4. Review, chỉnh sửa, loại bỏ hoặc bổ sung issue thủ công.
5. Chủ động bấm **Audit** để AI tạo Draft Issue Log DOCX trong background.
6. Tải DOCX của bất kỳ project version nào đã tạo output thành công.

AI là trợ lý phát hiện và soạn thảo. Auditor vẫn chịu trách nhiệm về judgement,
risk classification, nội dung được đưa vào output và việc chỉnh sửa/finalise
DOCX sau khi tải xuống.

## 3. Các quyết định sản phẩm đã chốt trong baseline

| ID | Quyết định |
|---|---|
| DEC-01 | UAT chỉ nhận folder upload từ local; không có SharePoint picker, sync hoặc publish. |
| DEC-02 | Upload/create project không tự chạy candidate discovery. Auditor phải bấm **Find candidates**. |
| DEC-03 | Candidate discovery và Audit là hai background jobs độc lập, durable và cho phép người dùng rời màn hình. |
| DEC-04 | File source của project bất biến sau khi project được tạo; không thêm, sửa, xóa hoặc thay thế file trong project. |
| DEC-05 | App cho sửa issue data nhưng không có editor cho DOCX/output do AI tạo. |
| DEC-06 | `observed_gap` và `evidence_summary` được giữ tách biệt. |
| DEC-07 | `evidence_refs` và `sop_refs` được chuẩn hóa thành `source_refs` có loại nguồn; hai field cũ chỉ là compatibility view nếu còn cần. |
| DEC-08 | Upload/Create project thành công phải tạo ngay audit version `v0.1`; version này tồn tại độc lập với discovery/Audit/DOCX status. |
| DEC-09 | Nút **+ New audit** tạo `v0.2+` theo sequence toàn project và lưu `base_version_id`; không yêu cầu version trước đã Audit thành công hoặc có DOCX. |
| DEC-10 | Nút **Audit** không tăng version; nó đóng băng input và gắn output DOCX vào current version. Filename phải chứa đúng current version. |
| DEC-11 | Guidelines và `template.docx` do app quản lý tập trung theo một bộ hiện hành; upload cùng tên overwrite bản cũ. `Samples/` là source context riêng của từng project, được đóng băng cùng source snapshot và không được dùng làm evidence/criteria. |
| DEC-12 | AI-discovered candidate bắt buộc có ít nhất một `EVIDENCE` ref và một `CRITERIA` ref; manual issue không bắt buộc hai ref này để Audit. |
| DEC-13 | `risk_category` là optional; AI gợi ý và auditor có thể giữ, đổi hoặc để trống. |
| DEC-14 | UAT chỉ hỗ trợ `.docx`, `.pdf`, `.xlsx`; mỗi Project artefact folder tối đa 20 files và tổng dung lượng tối đa 100 MB. |
| DEC-15 | UAT chưa có quantitative pass/fail threshold cho AI suggestions; auditor review thủ công và ghi nhận kết quả. |
| DEC-16 | Internal UAT không có application login, RBAC hoặc project-level authorization. Portal bị giới hạn ở corporate VPN/approved IP range. Entra ID được deferred sau UAT. |
| DEC-17 | Merge/Split UI và Cancel job được deferred; Retry sau failure là bắt buộc trong UAT. |

## 4. Phạm vi

### 4.1 In scope

- Browser folder picker và upload giữ nguyên relative path.
- Server-side validation cho folder structure, file metadata và khả năng đọc.
- Review folder tree và validation result trước khi tạo project.
- Project list, project detail và version history.
- Background candidate discovery với progress, retry và terminal state.
- Candidate Issue Register: AI candidates và manual issues dùng cùng một model.
- Issue create/edit/disposition; lưu nguồn gốc và audit trail.
- Background Audit để validate, draft và render DOCX.
- Download DOCX theo project version.
- Local/object storage cho raw input, intermediate artefacts và outputs trong UAT.
- Centrally managed, versioned Guidelines và DOCX style/template assets.

### 4.2 Out of scope

- SharePoint picker, connector, đồng bộ file hoặc publish output.
- Thêm, sửa, xóa hoặc thay thế source file sau khi project được tạo.
- Chỉnh sửa DOCX trong web app.
- Audit opinion, assurance conclusion hoặc tự động phê duyệt report.
- Final submission tới stakeholder hoặc hệ thống records management.
- Collaborative real-time editing.
- Autonomous agent tự thay đổi scope hoặc tự phát hành report.
- Merge/Split candidate UI và user-triggered Cancel background job trong UAT baseline.

## 5. Actors và quyền

### 5.1 Auditor (internal UAT)

- Tạo và xem project trong UAT environment; UAT không phân quyền theo user/project.
- Chạy discovery/Audit, xem progress và retry theo allowed actions.
- Tạo, sửa và disposition issue.
- Mở/chỉnh version bất kỳ, tạo **+ New audit** từ selected base version và tải output có sẵn.

### 5.2 System worker

- Validate/parse documents, tìm candidates, validate evidence/scope, draft và render.
- Ghi checkpoint, events, manifests và artefacts theo job.
- Không tự phê duyệt candidate thay auditor.

### 5.3 UAT administrator

- Xem lỗi kỹ thuật/correlation ID và hỗ trợ retry.
- Quản lý cấu hình artefact profile, giới hạn upload và retention.
- Không mặc định được xem raw audit content nếu không có quyền project.

## 6. Luồng nghiệp vụ

### 6.1 Luồng A — Upload và tạo project

```text
Select local folder
  → browser pre-check
  → upload to isolated staging
  → authoritative server validation
  → show folder tree + validation report
  → user confirms project name
  → Create project
  → freeze source snapshot
  → create audit version v0.1
  → READY_FOR_DISCOVERY
```

1. Tên project mặc định lấy từ folder gốc; auditor có thể đổi trước khi tạo.
2. Browser chỉ gửi file content và relative path, không gửi absolute local path.
3. Staging chưa phải project. Nếu có blocking error, auditor có thể chọn lại
   folder hoặc bỏ staging session.
4. Sau khi **Create project** thành công, source manifest và file content trở
   thành snapshot bất biến.
5. Hệ thống tạo `v0.1` trong cùng transaction promote project; không chờ
   discovery, Audit hoặc DOCX.
6. UI chỉ hiển thị lại tree/metadata; không cung cấp file mutation action.

### 6.2 Luồng B — Tìm candidate issues

```text
READY_FOR_DISCOVERY
  → user clicks Find candidates
  → DISCOVERY_QUEUED
  → PARSING → DISCOVERING → VALIDATING
  → CANDIDATES_READY (stored in current version v0.1)
     or INCOMPLETE / FAILED
```

- API nhận command và trả về ngay với `job_id`; request không chờ AI hoàn tất.
- User có thể đóng dialog, đổi project hoặc logout; job tiếp tục chạy.
- Reload/reconnect phải đọc lại snapshot và events, không làm chạy lại job.
- Khi thành công, candidate register được lưu vào current audit version `v0.1`;
  discovery không tạo hoặc tăng project version.

### 6.3 Luồng C — Review và nhập issue thủ công

Auditor có thể:

- xem candidate cùng gap, evidence, criteria, source location và risk gợi ý;
- sửa các business fields;
- approve, reject, mark needs evidence hoặc out of scope;
- tạo manual issue;
- mở một version bất kỳ để xem hoặc chỉnh issue của version đó;
- bấm **+ New audit** để tạo next version từ version đang chọn.

Thay đổi được autosave với optimistic concurrency và audit trail. Nếu version
đã có DOCX, edit mới đánh dấu output hiện tại là `STALE` nhưng không xóa file cũ.

### 6.4 Luồng D — Audit và tạo DOCX

```text
Current audit version
  → user clicks Audit
  → preflight validation
  → freeze audit-input snapshot
  → AUDIT_QUEUED
  → DRAFTING → FINAL_VALIDATION → RENDERING
  → success: attach new DOCX output revision to current version
     or INCOMPLETE / FAILED
```

- Audit cũng là background job và có progress/reconnect tương tự discovery.
- Issue edits sau thời điểm submit không được lọt vào audit đang chạy.
- Khi thành công, current version giữ issue snapshot đã dùng, provenance, run
  manifest và DOCX output revision. Audit không tạo version mới.
- App không mở DOCX để chỉnh sửa. Auditor tải file và chỉnh bằng công cụ ngoài.

### 6.5 Luồng E — Tạo và quay lại audit version

Ví dụ:

```text
Upload/Create project → v0.1
Find candidates + edit v0.1 → Audit → DOCX filename contains v0.1
Click + New audit from v0.1 → v0.2 (no DOCX required on v0.1)
Edit v0.2 → Audit → DOCX filename contains v0.2
Return to v0.1 → edit → v0.1 output becomes STALE → re-Audit v0.1
```

Version history phải hiển thị số version, `base_version_id`, timestamp, creator,
issue state, output availability và `CURRENT | STALE` output status. **+ New
audit** copy issue set của selected base version nhưng không copy DOCX. Mỗi Audit
run tạo một immutable output artefact revision; UI tải latest successful DOCX
của version, còn revision cũ được giữ trong audit trail.

## 7. Artefact intake và validation

### 7.1 Project artefact profile UAT

| Logical role | Folder mặc định | Requirement |
|---|---|---|
| Scope | `AWP/` | Bắt buộc, ít nhất một file được hỗ trợ và đọc được |
| Risk context | `APM/` | Bắt buộc, ít nhất một file được hỗ trợ và đọc được |
| Actual/evidence | `Process Understanding/` | Bắt buộc, ít nhất một file được hỗ trợ và đọc được |
| Criteria | `Process SOP/` | Bắt buộc cho AI discovery, ít nhất một criteria source được hỗ trợ và đọc được |
| Sample | `Samples/` | Không bắt buộc; dùng làm context tham khảo tone, wording và structure của riêng project |

Tên folder là mapping mặc định, không nên là business rule cứng trong pipeline.
Administrator có thể cấu hình alias và required role mà không đổi code.

`Guidelines` và `template.docx` không phải project artefacts. App quản lý một
bộ hiện hành dùng chung; upload mới overwrite file cùng tên và người dùng có thể
xóa qua central knowledge API. Mỗi Audit job vẫn đóng băng asset ID/hash và một
bản copy nội bộ để retry tái lập đúng input. `Samples/` là project artefact
optional, bất biến sau khi Create project và chỉ dùng làm drafting context,
không phải evidence hoặc criteria.

Allowlist UAT là `.docx`, `.pdf` và `.xlsx`. Tổng content length của một folder
upload không được vượt quá **100 MB (100,000,000 bytes)** và tổng số file không
được vượt quá **20 files**. Định dạng mới chỉ được bật khi có parser, provenance
rule và test fixture tương ứng.

### 7.2 Hai tầng validation

**Upload validation** phải kiểm tra:

- folder không rỗng; relative path an toàn và không trùng;
- tổng số file không quá 20 và total folder size không quá 100 MB;
- extension/MIME được hỗ trợ;
- file ẩn, temporary file, executable và archive nguy hiểm bị từ chối hoặc bỏ qua theo policy;
- malware scan hoàn tất trước khi promote khỏi quarantine.

**Content readiness validation** phải kiểm tra:

- các logical role bắt buộc hiện diện;
- mỗi role bắt buộc có ít nhất một file parse được;
- encrypted/password-protected/corrupt/zero-byte file được nêu rõ;
- AWP/APM có thể tạo scope boundary tối thiểu;
- có ít nhất một evidence source và một criteria source dùng được cho AI discovery.

Validation result gồm `errors`, `warnings`, file tree, detected roles và
`allowed_actions`. Warning không chặn project creation; error chặn.

### 7.3 Source snapshot

Mỗi document trong manifest phải có ít nhất:

- `document_id`, `relative_path`, `logical_role`;
- `content_hash`, size, MIME, modified time nếu browser cung cấp;
- upload/scan/parse status và parser version;
- storage object reference nội bộ.

## 8. Candidate Issue data contract

### 8.1 Business fields

| Field | Requirement | Ý nghĩa |
|---|---|---|
| `title_hint` | AI candidate: required; manual draft: optional | Gợi ý tiêu đề; Audit có thể refine theo writing guideline |
| `observed_gap` | Required trước Audit | Condition/gap thực tế đã quan sát, nêu khác biệt cụ thể |
| `evidence_summary` | AI candidate: required; manual issue: optional | Cách kiểm tra, population/sample, kết quả và exception hỗ trợ gap |
| `source_refs` | AI candidate: bắt buộc có `EVIDENCE` và `CRITERIA`; manual issue: optional | Danh sách nguồn evidence và criteria có phân loại |
| `risk_category` | Optional | AI gợi ý; auditor có thể giữ, đổi hoặc để trống |

Không gộp `observed_gap` và `evidence_summary` trong storage/API. Hai field có
thể được đặt trong cùng một UI section, nhưng phải vẫn là hai dữ liệu độc lập để:

- kiểm tra claim có được evidence hỗ trợ hay không;
- phân biệt condition với test procedure/result;
- tránh một đoạn văn dài khó validate và khó trace.

### 8.2 Unified source reference

Thay vì hai string arrays `evidence_refs` và `sop_refs`, dùng:

```json
{
  "source_refs": [
    {
      "ref_kind": "EVIDENCE",
      "document_id": "doc_01...",
      "location": "Sheet Access Review, rows 14-23",
      "quote": "optional short excerpt"
    },
    {
      "ref_kind": "CRITERIA",
      "document_id": "doc_02...",
      "location": "Section 4.2",
      "quote": "optional short excerpt"
    }
  ]
}
```

Lý do gộp container:

- criteria có thể đến từ policy, contract, guideline hoặc AWP chứ không chỉ SOP;
- cùng một reference model hỗ trợ file/page/section/sheet/cell;
- validator vẫn phân biệt evidence và criteria bằng `ref_kind`;
- tránh hai field song song có logic duplicate.

Trong giai đoạn migration, API có thể trả `evidence_refs` và `sop_refs` dưới
dạng derived compatibility fields; client mới không được ghi đồng thời cả hai
model.

### 8.3 System fields

Candidate/manual issue còn phải có:

- `issue_id`, `origin = AI_DISCOVERED | MANUAL`;
- `status`, `confidence`, `validation_flags`;
- `scope_ids`, `control_ids`, `fact_ids` nếu có;
- `created_by`, `created_at`, `updated_by`, `updated_at`;
- `row_version` để chống lost update.

Manual issue được phép Audit chỉ với `observed_gap`; `evidence_summary` và
`EVIDENCE`/`CRITERIA` refs là optional. Hệ thống phải giữ `origin = MANUAL`,
không được biến auditor input thành AI-verified evidence, và chỉ được bổ sung
claim mới nếu claim đó có nguồn. AI candidate thiếu evidence summary hoặc một
trong hai ref phải bị chặn khỏi Audit cho đến khi đủ nguồn.

## 9. Functional requirements

### 9.1 Project intake

| ID | Requirement | Acceptance summary |
|---|---|---|
| FR-INT-001 | Hệ thống phải cho chọn một local folder. | Browser gửi files + relative paths; không gửi absolute path. |
| FR-INT-002 | Hệ thống phải upload vào staging tách biệt theo user/session. | File của session/project khác không truy cập chéo được. |
| FR-INT-003 | Hệ thống phải validate folder ở server và trả report có cấu trúc. | Có error/warning/file/role; UI không parse text để quyết định action. |
| FR-INT-004 | Hệ thống phải hiển thị folder tree trước Create project. | Tree phản ánh manifest đã upload, không phải dữ liệu chỉ ở browser. |
| FR-INT-005 | Tên mặc định phải lấy từ root folder và cho đổi trước khi tạo. | Blank/duplicate name được xử lý theo policy; ID không phụ thuộc tên. |
| FR-INT-006 | Sau Create project, source files phải bất biến. | Không có API/UI add/replace/delete source document. |
| FR-INT-007 | Upload/create không được tự khởi động discovery. | Project kết thúc ở `READY_FOR_DISCOVERY`. |
| FR-INT-008 | App phải áp dụng allowlist `.docx`, `.pdf`, `.xlsx`, tối đa 20 files và 100 MB/folder. | Folder có file thứ 21, vượt 100,000,000 bytes hoặc có format ngoài allowlist bị từ chối có reason. |
| FR-INT-009 | App phải dùng Guidelines/template hiện hành do app quản lý tập trung và Samples thuộc project. | Project upload không thể override central assets; run manifest ghi đúng asset ID/hash; Samples nằm trong immutable source tree. |
| FR-INT-010 | Create project phải tạo atomically audit version `v0.1`. | API response có current version `v0.1` dù discovery/Audit chưa chạy. |

### 9.2 Candidate discovery

| ID | Requirement | Acceptance summary |
|---|---|---|
| FR-DIS-001 | `Find candidates` phải tạo background job idempotent. | Double-click/retry request không tạo hai active discovery jobs. |
| FR-DIS-002 | Job phải tiếp tục khi user rời màn hình. | Chuyển project/reload không cancel job. |
| FR-DIS-003 | Job phải phát durable progress và heartbeat. | Reconnect từ last event không mất/nhân đôi event. |
| FR-DIS-004 | AI candidate phải evidence-grounded và trong scope. | Có ít nhất một `EVIDENCE` và một `CRITERIA` ref trong project snapshot; ngoài scope không auto-approve. |
| FR-DIS-005 | Discovery phải lưu candidate register vào current version. | Discovery không tăng version; retry không tạo version duplicate. |
| FR-DIS-006 | Lỗi thiếu/không đọc được artefact phải phân biệt `INCOMPLETE` với lỗi kỹ thuật `FAILED`. | UI hiển thị corrective action phù hợp. |

### 9.3 Issue review

| ID | Requirement | Acceptance summary |
|---|---|---|
| FR-ISS-001 | Hệ thống phải hiển thị Candidate Issue Register theo audit version. | Mỗi issue có business fields, source, origin, status và row version. |
| FR-ISS-002 | Auditor phải tạo được manual issue chỉ với `observed_gap`. | `evidence_summary`, source refs và risk optional; issue có `origin=MANUAL` và được Audit khi các field này rỗng. |
| FR-ISS-003 | Auditor phải sửa và disposition issue. | Approve/reject/needs-evidence/out-of-scope có audit trail. |
| FR-ISS-004 | Edit phải dùng optimistic concurrency. | Conflict không ghi đè im lặng; UI yêu cầu resolve. |
| FR-ISS-005 | Auditor phải mở và chỉnh issue của version bất kỳ. | Edit có audit trail; DOCX hiện có chuyển `STALE` mà không bị xóa. |
| FR-ISS-006 | **+ New audit** phải tạo next `v0.N` từ selected version. | Copy issue set, lưu `base_version_id`, không copy DOCX và không yêu cầu base có output. |

**Merge** là gộp từ hai AI candidates gần trùng nhau thành một issue duy nhất,
đồng thời giữ toàn bộ source refs và lịch sử của hai candidate gốc. **Split** là
tách một candidate đang chứa nhiều gap/control không liên quan thành nhiều
issues độc lập. Hai UI commands này được deferred khỏi UAT; auditor đạt kết quả
tương đương bằng create/edit/reject, dù thao tác thủ công hơn.

### 9.4 Audit và output

| ID | Requirement | Acceptance summary |
|---|---|---|
| FR-AUD-001 | Audit phải chạy preflight theo origin trước khi enqueue. | AI candidate thiếu evidence/criteria bị block; manual issue không bị block chỉ vì thiếu refs. |
| FR-AUD-002 | Audit phải chạy background và dùng frozen input snapshot. | Edit sau submit không thay đổi output đang chạy. |
| FR-AUD-003 | AI không được tự thêm issue ngoài frozen selected set. | Mỗi drafted issue trace về `issue_id` nguồn. |
| FR-AUD-004 | Final validation phải chạy trước render. | Unsupported AI claim/invalid citation chặn output; manual input được giữ attribution và AI không được tự bổ sung unsupported claim. |
| FR-AUD-005 | Audit thành công phải attach output atomically vào current version. | Input snapshot, manifest và DOCX cùng được promote; Audit không tăng version. |
| FR-AUD-006 | Mỗi DOCX phải thuộc đúng một project version. | Download filename là `<Project Name>_Issue Log v0.N.docx`; hash, issue revision và created time được lưu. |
| FR-AUD-007 | Auditor phải tải được DOCX của mọi version có output ready. | Download không phụ thuộc version hiện đang checkout. |
| FR-AUD-008 | App không được cung cấp output content editor. | Chỉ preview metadata/status và download. |

### 9.5 History và recoverability

| ID | Requirement | Acceptance summary |
|---|---|---|
| FR-HIS-001 | **+ New audit** phải tăng project version đơn điệu `v0.N`. | Không reuse/overwrite version number; Audit command không tăng sequence. |
| FR-HIS-002 | Version phải lưu `base_version_id`. | New audit từ version cũ tạo next global number nhưng trace được base. |
| FR-HIS-003 | Failed job phải lưu attempt và error/correlation ID. | Không tạo DOCX ready giả và không làm mất latest successful output. |
| FR-HIS-004 | Retry phải idempotent theo frozen input hash. | Không tạo duplicate candidate/output khi worker retry. |
| FR-HIS-005 | Mọi create/edit/disposition/run/download phải có audit event. | Event có actor, action, timestamp, target và correlation ID. |
| FR-HIS-006 | Discovery và Audit failure phải có Retry action. | Retry dùng checkpoint/idempotency key và không tạo duplicate version/output. |
| FR-HIS-007 | Mỗi Audit run phải tạo immutable output artefact revision trong current version. | UI expose latest successful output; revision cũ còn trong audit trail. |

## 10. State models

### 10.1 Project state

```text
STAGING → VALIDATING_UPLOAD → READY_TO_CREATE
                                ↓
                       READY_FOR_DISCOVERY
                                ↓
                      CANDIDATES_AVAILABLE
                                ↓
                          OUTPUT_AVAILABLE
```

Project state là read model tổng hợp. Job state không được nhồi vào một trường
project status duy nhất.

Audit version có state riêng:

```text
DRAFT → CANDIDATES_READY → AUDITING → DOCX_READY
          ↑       edit after output       ↓
          └──────────── STALE_OUTPUT ─────┘
```

Version tồn tại ngay khi được tạo; `DOCX_READY` không phải điều kiện để version
được coi là hợp lệ hoặc để tạo **+ New audit** tiếp theo.

### 10.2 Job state

```text
QUEUED → RUNNING → SUCCEEDED
                 → INCOMPLETE
                 → FAILED
```

`job_type = DISCOVERY | AUDIT`; stage chi tiết nằm trong progress event.
`CANCELLED` được reserved cho phase sau nhưng UAT baseline không cung cấp
user-triggered Cancel action.

Nếu được triển khai sau này, **Cancel** nghĩa là gửi yêu cầu dừng job tại safe
checkpoint tiếp theo. Hệ thống không kill transaction hoặc LLM request đang bay;
request hiện tại có thể hoàn tất nhưng kết quả không được promote thành version.

### 10.3 Issue state

```text
DRAFT → READY_FOR_REVIEW → APPROVED
                         → NEEDS_EVIDENCE
                         → REJECTED
                         → OUT_OF_SCOPE
```

Chỉ issue được chọn và đủ điều kiện mới đi vào Audit input snapshot.

## 11. Non-functional requirements

### 11.1 Security và privacy

| ID | Requirement |
|---|---|
| NFR-SEC-001 | Portal UAT chỉ được truy cập từ corporate VPN/approved corporate IP range; UAT không có application login hoặc authorization theo user/project. |
| NFR-SEC-002 | Data phải được mã hóa in transit và at rest. |
| NFR-SEC-003 | Raw document text/full prompts không được ghi vào application log mặc định. |
| NFR-SEC-004 | Upload phải có quarantine, MIME allowlist, size/count limits và malware scan trước xử lý. |
| NFR-SEC-005 | Staging session hết hạn phải được cleanup theo policy; project source/output retention phải cấu hình riêng. |
| NFR-SEC-006 | DOCX download phải đi qua internal UAT application endpoint; không dùng S3 bucket/object public. |
| NFR-SEC-007 | Entra ID login và RBAC là scope sau UAT; không phải release dependency của UAT. |

### 11.2 Reliability

| ID | Requirement |
|---|---|
| NFR-REL-001 | Job state, checkpoints và events phải durable qua API/worker restart. |
| NFR-REL-002 | Stage handler phải idempotent theo job/stage/input hash. |
| NFR-REL-003 | Không được có hơn một active discovery hoặc Audit job cho cùng working snapshot. |
| NFR-REL-004 | Output chỉ ở trạng thái ready sau khi file được ghi xong, checksum hợp lệ và metadata commit thành công. |

### 11.3 Performance và usability

| ID | Requirement |
|---|---|
| NFR-PERF-001 | Command tạo background job nên phản hồi trong 2 giây ở tải UAT bình thường, không tính upload bytes. |
| NFR-PERF-002 | Progress snapshot phải khôi phục sau reload; SSE là ưu tiên, polling là fallback. |
| NFR-PERF-003 | Không hiển thị phần trăm giả; dùng item counts hoặc indeterminate progress khi không ước lượng được. |
| NFR-UX-001 | UI phải phân biệt upload progress, discovery progress và Audit progress. |
| NFR-UX-002 | Mọi disabled action phải hiển thị lý do và bước khắc phục. |
| NFR-UX-003 | Version history phải cho biết version state, base version, DOCX availability và output `CURRENT | STALE`. |

### 11.4 AI quality và traceability

| ID | Requirement |
|---|---|
| NFR-AI-001 | Mọi claim do AI discovery/drafting bổ sung phải trace tới source reference; manual auditor input có thể không có ref nhưng phải giữ `origin=MANUAL`. |
| NFR-AI-002 | Chỉ centrally managed Guidelines/template được dùng cho tone/format; chúng không làm evidence của candidate. |
| NFR-AI-003 | Run manifest phải lưu model ID, prompt/schema/parser version, source hashes, duration và validation result. |
| NFR-AI-004 | UAT phải cho auditor review thủ công AI suggestions và lưu disposition/comment; chưa dùng quantitative threshold để quyết định pass/fail. |

## 12. Release plan để kiểm soát tiến độ

Tên release dùng `UAT-RN` để tránh nhầm với project content version `v0.N`.

### UAT-R1 — Project intake foundation

Phạm vi:

- `FR-INT-001` đến `FR-INT-010`;
- source manifest và folder tree;
- project list/detail tối thiểu;
- upload security tối thiểu cho môi trường UAT.

Exit criteria:

- Upload Lumina Grand từ browser và nhận cùng relative tree/hash ở backend.
- Thiếu AWP hoặc file corrupt tạo blocking validation có thể hiểu được.
- Folder có hơn 20 files, vượt 100 MB hoặc có format ngoài allowlist bị từ chối.
- Guideline/template trong upload không override asset trung tâm.
- Create project trả về current version `v0.1` trước khi discovery/Audit chạy.
- Project hợp lệ dừng ở `READY_FOR_DISCOVERY` và không tự gọi LLM.
- Không có API/UI thay đổi source file sau Create project.

### UAT-R2 — Candidate discovery and review

Phạm vi:

- `FR-DIS-*`, `FR-ISS-*`;
- durable job/events/reconnect;
- candidate register theo current audit version;
- manual issue và versioned issue editing.

Exit criteria:

- Find candidates tiếp tục khi user đổi màn hình và phục hồi sau reload.
- Mỗi candidate hiển thị condition, evidence summary, typed source refs và risk.
- Auditor có thể chỉnh/reject/thêm manual issue trong `v0.1`.
- Discovery retry không tạo candidate/version duplicate.

### UAT-R3 — Audit, DOCX and version history

Phạm vi:

- `FR-AUD-*`, `FR-HIS-*`;
- **+ New audit**, frozen audit input, final validation và DOCX renderer;
- version navigation/history/download và stale-output handling.

Exit criteria:

- **+ New audit** tạo `v0.2` từ `v0.1` dù `v0.1` chưa có DOCX.
- Audit trên `v0.1` tạo DOCX filename chứa `v0.1` và không tăng version.
- Edit trong lúc Audit chạy không thay đổi DOCX của job đó.
- Edit version đã có output đánh dấu `STALE`; re-Audit tạo output revision mới.
- Tải được DOCX của từng output version; app không có output editor.

### UAT-R4 — Hardening and UAT acceptance

Phạm vi:

- NFR security/reliability/observability còn lại;
- retry, cleanup/retention, automated E2E;
- manual AI suggestion review record và operational runbook.

Exit criteria:

- Worker/API restart không mất job/event hoặc tạo output duplicate.
- Internal network restriction và private-output download được kiểm thử.
- UAT test set có auditor disposition/comment cho AI suggestions; không áp quantitative pass/fail threshold.
- Auditor ký nhận workflow và DOCX đủ dùng để chỉnh sửa ngoài app.

## 13. UAT scenarios tối thiểu

| ID | Scenario | Expected result |
|---|---|---|
| UAT-01 | Upload folder hợp lệ | Tree đúng, validation pass, tạo project được |
| UAT-02 | Thiếu AWP | Blocking error; không Create project |
| UAT-03 | Có file unsupported/corrupt | File-level error/warning rõ; action đúng policy |
| UAT-04 | Find candidates rồi chuyển sang project khác | Job tiếp tục; quay lại thấy đúng progress/result |
| UAT-05 | Reload trong discovery | Không restart job; events phục hồi không duplicate |
| UAT-06 | AI candidate có source ngoài project | Candidate bị block/quarantine |
| UAT-07 | Thêm manual issue không có evidence/criteria refs | Save và Audit được; output giữ origin/manual attribution, AI không thêm unsupported claim |
| UAT-08 | Audit rồi sửa current version ngay | Output chỉ chứa frozen snapshot lúc submit |
| UAT-09 | Audit thành công trong `v0.1` | Version vẫn là `v0.1`; filename chứa `v0.1`; DOCX attach đúng version |
| UAT-10 | **+ New audit** khi `v0.1` chưa có DOCX | Tạo `v0.2`, copy issues, `base_version_id=v0.1`, không copy output |
| UAT-11 | Audit fail giữa render | Không có DOCX partial; attempt có error; latest successful output không mất |
| UAT-12 | Download hai version khác nhau | Trả đúng file/hash/version tương ứng |
| UAT-13 | Thử gọi file mutation API | Không có capability hoặc bị từ chối |
| UAT-14 | Request portal từ IP ngoài allowlist | Không truy cập được portal |
| UAT-15 | Edit version đã có DOCX | Output thành `STALE`; file cũ còn tải được; re-Audit tạo revision mới |

## 14. Traceability matrix theo release

| Capability | Requirements | Release |
|---|---|---|
| Local folder + validation | `FR-INT-*`, `NFR-SEC-004` | `UAT-R1` |
| Immutable project source | `FR-INT-006`, `FR-HIS-005` | `UAT-R1` |
| Background discovery | `FR-DIS-*`, `NFR-REL-001..003` | `UAT-R2` |
| Candidate/manual review | `FR-ISS-*`, `NFR-AI-001..002` | `UAT-R2` |
| Background Audit + DOCX | `FR-AUD-*`, `NFR-REL-004` | `UAT-R3` |
| Version creation/navigation/history | `FR-ISS-005..006`, `FR-HIS-*`, `NFR-UX-003` | `UAT-R3` |
| Security/recovery/quality | `NFR-*` | `UAT-R4` |

## 15. Decision status và dependencies còn lại

### 15.1 Đã chốt cho baseline

- Guidelines và `template.docx` dùng bộ hiện hành do app quản lý tập trung; `Samples/` là immutable source context theo project.
- AI candidate cần cả evidence và criteria; manual issue không bắt buộc hai ref này.
- `risk_category` optional, AI suggest và auditor có thể thay đổi.
- Merge/Split UI deferred; UAT dùng create/edit/reject để đạt kết quả tương đương.
- Retry sau failure bắt buộc; Cancel action deferred.
- Chỉ hỗ trợ `.docx`, `.pdf`, `.xlsx`; mỗi folder tối đa 20 files và 100 MB.
- AI suggestions được auditor review thủ công; chưa có quantitative pass/fail threshold.
- Internal UAT không có app login/RBAC; access được giới hạn bằng corporate VPN/approved IP range.

### 15.2 Còn phụ thuộc hoặc cần xác nhận

1. Corporate VPN/approved IP range và internal UAT HTTPS endpoint.
2. Retention cho staging, source snapshot và DOCX output.

## 16. Definition of Done của toàn bộ UAT scope

- Bốn release exit criteria đã pass và có test evidence.
- Không có source file mutation sau Create project.
- Discovery và Audit đều background, durable và recoverable.
- Candidate/manual issue có traceability và review history.
- Create project tạo `v0.1`; chỉ **+ New audit** tăng version và lưu đúng base.
- Audit attach DOCX vào current version; edit/re-Audit giữ output revision history.
- Mỗi output-ready version tải đúng DOCX và manifest của nó.
- Không có blocking evidence/scope/validation error trong output.
- Auditor xác nhận DOCX đủ tốt để tiếp tục chỉnh sửa bên ngoài app.
- Các open decisions đã được đóng hoặc ghi rõ là deferred với owner/date.
