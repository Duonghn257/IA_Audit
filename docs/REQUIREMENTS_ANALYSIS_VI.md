# Phân tích yêu cầu dự án (tiếng Việt)
**Dự án**: Operation Report Jedi – AI‑Assisted Audit Issue Log Drafting (POC)  
**Mục đích tài liệu**: Làm rõ yêu cầu để team thống nhất “phải làm gì / không làm gì”, tiêu chí thành công, và đầu vào–đầu ra của hệ thống.

> Nguồn tham chiếu chính: `Functional Specification - Operation Report Jedi.docx` và bộ artefacts mẫu trong `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/`.

---

## 1) Bối cảnh & vấn đề
Internal Audit đang **soạn thảo issue log thủ công** → tốn thời gian và dễ **không nhất quán** về cấu trúc, giọng văn, thuật ngữ, formatting giữa các báo cáo.  
Operation Report Jedi là **POC** để đánh giá việc dùng AI như **trợ lý soạn thảo** (drafting assistant) dựa trên **tài liệu IA đã phê duyệt**.

---

## 2) Mục tiêu (Objectives)
Hệ thống cần đạt:
- **Soạn thảo nháp Issue Log có cấu trúc chuẩn** (Finding/Impact/Recommendation…) để auditor chỉnh sửa nhanh hơn.
- **Chuẩn hoá** ngôn ngữ và formatting theo chuẩn IA.
- **Giảm effort soạn thảo** nhưng vẫn giữ **auditor judgement & accountability**.
- Đảm bảo output AI **tuân thủ**:
  - **Scope** của cuộc audit (theo AWP)
  - **Risk focus** (theo APM)
  - **SOP/Policy** và artefacts đã cung cấp
  - **Guidelines** về writing/formatting

---

## 3) Phạm vi POC (Scope)

### 3.1 In-scope
- AI **hỗ trợ soạn thảo Audit Issue Logs** (nháp) cho từng project audit.
- Dùng **10 audit projects đã hoàn tất** làm dataset tham chiếu/huấn luyện/đối chiếu.
- Output nháp phải theo **Issue Log Template** và các chuẩn trong thư mục `Guidelines/`.

### 3.2 Out-of-scope (không làm trong POC)
- AI **không** thực hiện audit testing, control evaluation.
- AI **không** đưa ra audit opinion/assurance conclusion.
- AI **không** tự động finalise/submission báo cáo khi chưa có người review.
- Chưa triển khai workflow “3-agent end-to-end” (Harvester/Sorter/Review Agent) trong POC (để pha sau).
- AI **không** thay đổi scope/risk assessment đã phê duyệt.

---

## 4) Stakeholders & trách nhiệm
- **Auditor/IA Team**: cung cấp input issue, review/edit, chịu trách nhiệm cuối.
- **Project Lead/Tech Lead**: thiết kế & vận hành hệ thống, guardrails, audit trail.
- **IT/Security/Compliance** (nếu có): kiểm soát truy cập dữ liệu, phê duyệt vendor/NDA.
- **Vendor/Platform** (tuỳ): cung cấp model/service hạ tầng (đảm bảo governance).

---

## 5) Input & Output (đầu vào – đầu ra)

### 5.1 Input bắt buộc (artefacts theo thư mục)
Hệ thống sử dụng **chỉ** các tài liệu IA phê duyệt theo nhóm:
- **`Samples/`**: issue logs lịch sử &/hoặc report mẫu để học format/tone/vocabulary.
- **`Process Understanding/`**: mô tả quy trình, context kiểm soát, **issue/evidence** auditor ghi nhận.
- **`Guidelines/`**: chuẩn viết & formatting IA (tone, font, tables, cross-reference…).
- **`Process SOP/`**: SOP/Policy làm benchmark “should-be”.
- **`AWP/` (Approved Work Program)**: scope/objectives và boundary (để chặn vượt scope).
- **`APM/` (Approved Planning Memo)**: risk focus/audit intent (để ưu tiên trọng điểm).

### 5.2 Input từ người dùng (auditor)
Trong luồng POC, auditor cung cấp:
- **Issue-specific inputs**: observed gap, evidence summary (hoặc tham chiếu đến evidence trong Process Understanding).
- Tuỳ chọn: **số lượng issues** mong muốn để AI tạo đúng số lượng.

### 5.3 Output
- **Draft Issue Log** theo template (ví dụ bảng: `Findings | Possible Impact | Recommendations | Comments` và content/index page liệt kê issue codes + risk level + page).
- Lưu vào `Output/` theo naming:
  - `<Project Title>_Issue Log v0.1`
  - Rerun: tăng version **v0.2, v0.3…**, và **overwrite** draft trước.

---

## 6) Yêu cầu chức năng (Functional Requirements)

### FR1 — Sinh nháp Issue Log theo template
Hệ thống phải:
- Tạo draft issue dựa trên **input của auditor** và **artefacts** (Samples/Process Understanding/SOP/APM/AWP/Guidelines).
- Điền đủ các section bắt buộc theo Issue Log Template.
- Trình bày theo chuẩn trong `Guidelines/` (tone, spacing, tables, cross-reference…).

### FR2 — Context awareness (bám bằng chứng & benchmark)
Hệ thống phải:
- Dùng `Process Understanding/` + `Process SOP/` để “frame” issue (cái gì xảy ra vs cái gì đáng ra phải xảy ra).
- **Không đưa giả định/khẳng định** nếu không có căn cứ trong artefacts.

### FR3 — Scope control (không vượt AWP)
Hệ thống phải:
- Giới hạn output trong scope theo `AWP/`.
- Phản ánh ưu tiên theo `APM/`.
- Ngăn sinh issues ngoài audit scope.

### FR4 — Quản lý phiên bản output
Hệ thống phải:
- Khi rerun, tạo file mới với version tăng (v0.x) theo convention và overwrite bản trước theo yêu cầu spec.

### FR5 — Luồng sử dụng (POC)
Hệ thống phải hỗ trợ:
- Auditor trigger drafting sau khi fieldwork/evidence đã validate.
- Auditor review/edit/finalise draft.

---

## 7) Yêu cầu phi chức năng (Non-functional Requirements)

### NFR1 — Bảo mật & quản trị dữ liệu
- Tài liệu IA là **confidential**: chỉ người được phép truy cập.
- Output không suy luận/tiết lộ thông tin ngoài artefacts cung cấp.
- Nếu có vendor: yêu cầu **NDA/legal approvals**.

### NFR2 — Auditability / Traceability (khuyến nghị bắt buộc trong triển khai)
Để giảm rủi ro “AI bịa”, hệ thống nên lưu:
- Tài liệu nào đã được dùng cho mỗi issue (có thể ở mức đoạn/section).
- Input auditor và timestamp/rerun version.

### NFR3 — Chất lượng đầu ra
- Draft phải “refinement-ready”: auditor chỉnh sửa nhẹ, không phải viết lại từ đầu.
- Tone/format nhất quán theo Guidelines.

---

## 8) Ràng buộc trọng yếu (Constraints / Guardrails)
Đây là “đường ray” để giải pháp không đi chệch:
- **Evidence-grounded**: mọi nội dung quan trọng phải dựa trên artefacts (đặc biệt Process Understanding + SOP).
- **Không vượt scope**: không tạo issue ngoài AWP; không thêm nội dung ngoài mục tiêu audit.
- **Đúng format**: tuân Guidelines + template (tone “positive” cho tiêu đề issue khi yêu cầu, cross-reference chuẩn, font/table rules…).
- **Human-in-the-loop**: auditor là người duyệt cuối.

---

## 9) Tiêu chí thành công / Acceptance Criteria (POC)
POC được coi là đạt nếu:
- Draft tuân thủ structure/format IA (Guidelines + template).
- Có **giảm effort** soạn thảo (đo lường được).
- Output cần **refine** chứ không “full redraft”.
- Khi test trên completed audits, draft “gần” với report đã duyệt về structure/tone/key messaging.
- **Không có** scope breach và **không có** unsupported assertions (hoặc các điểm này được gắn cờ rõ ràng để auditor xử lý).

---

## 10) Deliverables (những thứ team phải bàn giao)
Tối thiểu cho POC:
- Công cụ/ứng dụng tạo **Draft Issue Log** từ bộ artefacts theo cấu trúc thư mục.
- Cơ chế output versioning (`v0.1`, `v0.2`…).
- Bộ tiêu chí kiểm thử POC (test set 10 audits) + cách đo “time saved/quality”.

Khuyến nghị mạnh (để POC đáng tin):
- Cơ chế trace (issue → nguồn artefact) + log rerun.
- Bộ kiểm tra scope/format cơ bản (lint rules).

---

## 11) Những câu hỏi còn mở (để chốt requirement trước khi thiết kế kiến trúc)
Các câu hỏi này quyết định hướng kỹ thuật, nhưng **không đổi bản chất yêu cầu**:
- **Dữ liệu**: có bắt buộc giữ on‑prem/VPC (data residency) không?
- **UI/UX**: POC dùng CLI/script hay web app nội bộ?
- **Mức tự động hoá input**: auditor nhập “gap/evidence summary” đến đâu? Có cần tự trích xuất “gaps” từ Process Understanding không?
- **Định nghĩa “supported evidence”**: có yêu cầu trích dẫn page/section rõ ràng không?
- **Format enforcement**: cần xuất DOCX chuẩn 100% như template hay chấp nhận DOCX “gần đúng” (để auditor sửa)?

---

## 12) Glossary (thuật ngữ)
- **Issue Log**: tài liệu liệt kê các issue/finding (Finding/Impact/Recommendation/Management response…) theo template IA.
- **APM**: Approved Planning Memo (risk focus/audit intent).
- **AWP**: Approved Work Program (scope/objectives/boundary).
- **SOP**: Process SOP/Policy (benchmark).
- **Process Understanding**: workpaper mô tả “as-is”, evidence và nhận định IA.
- **Guidelines**: chuẩn viết/formatting issue log.

