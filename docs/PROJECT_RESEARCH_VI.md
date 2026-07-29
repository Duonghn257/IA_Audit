# Ghi chú nghiên cứu dự án (tiếng Việt)

Tài liệu này tổng hợp những gì mình đã đọc/chiết xuất từ bộ tài liệu trong thư mục `IA Audit Report use case/` để giúp bạn **hiểu dự án Operation Report Jedi (POC)** và **biết cần làm gì tiếp theo**.

## 1) Tổng quan: Operation Report Jedi là gì?

Theo `Functional Specification - Operation Report Jedi.docx`, **Operation Report Jedi** là một **Proof of Concept (POC)** trong “AI Initiative” nhằm dùng AI để **hỗ trợ auditor soạn thảo Audit Issue Log** (nháp), giúp:

- **Giảm công sức soạn thảo thủ công** nhưng vẫn giữ **phán đoán & trách nhiệm cuối cùng** thuộc về auditor.
- **Tăng tính nhất quán** về cấu trúc, giọng điệu (tone), thuật ngữ và định dạng giữa các báo cáo.
- **Tuân thủ chuẩn IA** và **không vượt phạm vi** theo AWP/APM; không bịa/không suy diễn ngoài tài liệu được cung cấp.

### 1.1 Mục tiêu (Objectives)

- Hỗ trợ viết issue log có cấu trúc, chuyên nghiệp.
- Chuẩn hóa ngôn ngữ/format.
- Giảm “drafting effort”.
- Đảm bảo output AI **tuân thủ tiêu chuẩn IA** và các tài liệu được phê duyệt.

### 1.2 Phạm vi POC (Scope)

**In-scope**

- Chỉ **AI-assisted drafting audit issue logs**.
- Dùng **10 dự án audit đã hoàn tất** làm tập tham chiếu/huấn luyện.
- Sinh các phần chính trong issue log: **Finding/Issue**, **Impact**, **Recommendation**, áp dụng tone/format IA.

**Out-of-scope**

- AI **không làm audit testing**, không đánh giá hiệu quả kiểm soát, không kết luận assurance/opinion.
- Chưa triển khai “3-agent end-to-end” (Harvester/Sorter/Review) trong POC (để pha sau).
- Không sửa scope/risk assessment đã phê duyệt.
- Không tự động finalise/nộp báo cáo khi chưa có người review.

## 2) Mô hình dữ liệu đầu vào (Input Artefacts) & ý nghĩa các thư mục

Trong spec, AI phải tham chiếu các “artefacts” theo nhóm thư mục. Dự án mẫu của bạn (`IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/`) đang đúng cấu trúc này:

- `**Samples/`**
  - Chứa issue log template & báo cáo/artefact lịch sử để AI học “chuẩn đầu ra” (vocab, tone, cách trình bày).
- `**Process Understanding/**`
  - Chứa mô tả quy trình, bối cảnh kiểm soát, bằng chứng và phát hiện (control/gap/lapse/enhancement) do auditor ghi nhận.
- `**Guidelines/**`
  - Chuẩn viết & định dạng IA (format, tone, font, bảng, cross-reference…).
- `**Process SOP/**`
  - Quy trình/chính sách được phê duyệt (source of truth) để đối chiếu “should-be”.
- `**AWP` (Approved Work Program)**
  - Định nghĩa **scope & objectives** cho cuộc audit; dùng để **chặn vượt scope**.
- `**APM` (Approved Planning Memo)**
  - “Risk focus & audit intent”; giúp AI hiểu ưu tiên rủi ro và ngữ cảnh.
- `**Output/`**
  - Nơi lưu bản nháp AI tạo ra (theo quy ước đặt tên/version).

## 3) Yêu cầu chức năng chính (Functional Requirements) rút ra từ spec

### 3.1 Draft issue log

Hệ thống phải:

- Sinh nháp issue dựa trên **input của auditor**, đồng thời tham chiếu:
  - Format/ví dụ từ `Samples/`
  - Issue/evidence trong `Process Understanding/`
  - Tài liệu `APM`, `AWP`, `Process SOP`
- Điền đủ các mục bắt buộc theo **Issue Log Template**.
- Lưu output vào `Output/` theo tên: `<Project Title>_Issue Log v0.1`, rerun thì tăng version (v0.2, v0.3...) và **overwrite** bản trước.
- Dùng ngôn ngữ Internal Audit chuyên nghiệp, tuân theo `Guidelines/`.

### 3.2 Context Awareness

- Bám `Process Understanding` + `SOP` để **contextualise** phát hiện.
- “Frame” issue theo procedure/control đã phê duyệt.
- **Không đưa giả định/chi tiết không có trong artefacts**.

### 3.3 Scope Control

- Giới hạn output trong ranh giới `AWP`.
- Phản ánh ưu tiên rủi ro theo `APM`.
- Ngăn tạo issue ngoài phạm vi.

### 3.4 User interaction flow (POC)

Luồng làm việc được mô tả:

- Auditor hoàn tất fieldwork (bằng chứng đã thu thập/validate) rồi trigger drafting.
- Auditor cung cấp input issue (gap + evidence summary, và có thể cung cấp số lượng issue).
- AI sinh nháp issue log.
- Rerun: overwrite + tăng version.
- Auditor review/edit/finalise. **AI chỉ là drafting assistant.**

### 3.5 Security/Governance

- Tài liệu đều confidential; chỉ user được phép mới truy cập.
- Output không được suy luận/tiết lộ ngoài tài liệu đưa vào.
- Vendor involvement cần NDA/legal approvals.

## 4) Những gì mình đọc từ bộ tài liệu “Lumina Grand” (IA2024-02)

### 4.1 `APM` (Planning memo) — điểm nổi bật phục vụ “scope & context”

Từ bản text chiết xuất của `Lumina Grand_2. APM (8 Mar) (V3).docx`:

- Scope/risk liên quan:
  - **Product Sales**
  - **Pricing/Discount Management**
  - **Commission & Incentive Management**
  - **PDPA** (Collection & Care of Personal Data)
- Thông tin dự án: Lumina Grand EC 512 units, mở bán theo 2 phases, hệ thống **CDL Home Sales (CHS)** thay SAP từ Nov 2023.
- PDPA là **process mới** (chưa audit cho residential project trước đó) → IA sẽ kiểm tra tuân thủ PDPA + CDL PDPA Policy.
- APM cũng ghi nhận các “concerns”/pending RFI và bối cảnh nhân sự/turnover.

### 4.2 `AWP` (Work Program) — ranh giới & các thủ tục IA

Từ bản text chiết xuất của `Lumina Grand_5. AWP (8 Mar) (V3).docx`:

- AWP liệt kê các sub-process và work program tóm tắt + phân bổ man-days.
- In-scope gồm (tóm lược):
  - Control Environment (OM, Approval Matrix, Segregation of Duties)
  - Product Sales: Pricing/Discount; Commission/Incentives; kèm data analytics
  - PDPA: Collection & Care of personal data (walkthrough; compliance check)
- AWP là “gate” để AI **không vượt scope**.

### 4.3 `Guidelines` — chuẩn format issue log (v1.1)

Từ `Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf` (16 trang):

- Font: Arial 10 (body), Arial 9 (exception tables).
- British spelling; quy tắc viết abbreviations.
- Quy tắc bullet/multilevel list; alignment; page/section breaks.
- Quy tắc exception tables (header bold/grey shade, alignment, units, numbering…).
- Quy tắc cross-reference câu chuẩn: “Refer to Table A1-1 for more details”.
- Yêu cầu tone (issue header “positive tone”).
- Footer/header quy định; page numbers; “CONFIDENTIAL” ở footer.

### 4.4 `Process SOP` — PDPA policy/manual (benchmark “should-be”)

Đã đọc 2 PDF trong `Process SOP/`:

- `CDL PDPA Manual - Final v1.pdf`: manual PDPA, định nghĩa, obligations, annexes, quy trình xử lý…
- `PDPA CDL Personal Data Policy Aug 2018_FINAL.pdf`: policy dạng “public-facing/summary” nêu cách thu thập/sử dụng/disclose personal data, các tình huống thu thập phổ biến, v.v.

### 4.5 `Process Understanding` — evidence/control notes (benchmark “as-is”)

Từ `Process Understanding - Lumina Grand PDPA.docx` (chiết xuất text):

- Tài liệu có cấu trúc theo IA workpaper: objectives/risks/procedures, và phần “Process Understanding Findings”.
- Có tagging kiểu `[CONTROL]`, `[GAP]`, `[ENHANCEMENT]`, `[LAPSE]` (rất phù hợp để AI map sang draft issue).
- Mô tả chi tiết kênh thu thập dữ liệu cá nhân, cách đảm bảo các PDPA obligations (consent/notification/purpose limitation/accuracy/protection), flow dữ liệu giữa HDB E-apps, SFTP, CHS, Salesforce/Dow Jones (AML screening), OTP stage, v.v.

### 4.6 `Samples` — ví dụ output cuối & template

- `1. Issue Log Template_version 11 Oct 2023.docx`: template/structure issue log (bản text cho thấy phần “Issues / Audit Risk Level / Page…” và layout issue theo S/N, Findings, Possible Impact, Recommendations, Comments…).
- `FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf`: báo cáo audit đã phát hành; phần đọc được cho thấy kết luận audit, scope & methodology, background info… (dùng để đối chiếu chất lượng/tone).

## 5) “Bạn cần làm gì?” — checklist triển khai POC (thực dụng)

### 5.1 Chuẩn hóa dữ liệu đầu vào

- Chuẩn hóa cấu trúc thư mục cho mỗi audit (Samples/Process Understanding/Guidelines/Process SOP/APM/AWP/Output).
- Chọn **10 completed audits** theo tiêu chí POC và đảm bảo đủ artefacts “approved”.

### 5.2 Thiết kế input form cho auditor

Tối thiểu cần:

- Sub-process / chủ đề issue (để đối chiếu scope AWP).
- Observed gap + evidence summary (có thể trích dẫn bảng/số liệu).
- Mức độ rủi ro (nếu IA có rule).
- Số lượng issue mong muốn (spec có đề cập).

### 5.3 Pipeline sinh issue log (khuyến nghị)

Thứ tự an toàn:

- Đọc `AWP` + `APM` trước → xác định scope/ưu tiên.
- Đọc `Process SOP` → benchmark “should-be”.
- Đọc `Process Understanding` → “as-is”, evidence, control tags.
- Dự thảo issue theo `Issue Log Template`.
- Áp `Guidelines` để chuẩn hóa tone/format/cross-reference/tables.

### 5.4 Guardrails (bắt buộc để đạt success criteria)

- **Không bịa**: mọi assertion phải “trace” được về artefacts (đặc biệt Process Understanding + SOP).
- **Scope check**: chặn issue ngoài AWP.
- **Tone/format check**: đảm bảo “positive tone” cho title, font/table rules, British spelling (nếu áp).
- **Rerun/versioning**: xuất file đúng convention, overwrite + tăng v0.x.

### 5.5 Đánh giá thành công POC (Success Criteria)

Theo spec, POC thành công khi:

- Draft tuân chuẩn IA (structure/format).
- Auditor giảm thời gian soạn thảo (đo được).
- Output cần “refine” hơn là viết lại từ đầu.
- Khi test trên completed audits, draft “close” với report đã duyệt (về structure/tone/key messaging).
- Không có scope breach / unsupported assertions.

## 6) Danh sách tài liệu đã được đọc/chiết xuất (để truy vết)

- `Functional Specification - Operation Report Jedi.docx` (đã convert sang text để đọc).
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Guidelines/Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf`
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/APM/Lumina Grand_2. APM (8 Mar) (V3).docx` (đã convert text)
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/AWP/Lumina Grand_5. AWP (8 Mar) (V3).docx` (đã convert text)
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process Understanding/Process Understanding - Lumina Grand PDPA.docx` (đã convert text)
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process SOP/CDL PDPA Manual - Final v1.pdf`
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process SOP/PDPA CDL Personal Data Policy Aug 2018_FINAL.pdf`
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Samples/1. Issue Log Template_version 11 Oct 2023.docx` (đã convert text)
- `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Samples/FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf`
