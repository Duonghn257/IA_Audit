## Q&A — Operation Report Jedi (định hướng Web App/Portal)

Bối cảnh: build thành **web app** để user **tự nhập `sample_issues`** trên UI, bấm **Run audit**, hệ thống chạy pipeline và trả **kết quả + tải về DOCX**.

---

### 1) Có bắt buộc phải dùng Amazon Bedrock không? Hay chỉ cần LLM (Claude)?

**Không bắt buộc Bedrock.** Kiến trúc chỉ cần một **LLM endpoint** (Claude) đáp ứng:
- Context window đủ lớn (để nạp Guidelines/SOP/PU/Samples + constraints + auditor input).
- Hỗ trợ output **JSON có cấu trúc** ổn định (constraints/draft/validation).

Các lựa chọn phổ biến:
- **Claude qua Anthropic API** (direct).
- **Claude qua Bedrock** (nếu org đã chuẩn hoá AWS, IAM, logging).
- Claude qua một gateway nội bộ (nếu có).

Tóm lại: **Bedrock chỉ là “cổng gọi Claude”** trong 1 phương án triển khai.

---

### 2) S3 dùng để làm gì? Có cần thiết không?

Trong proposal, **S3 là “optional”**. Nó thường dùng để:
- **Lưu dataset/projekt artefacts** dùng chung (khi nhiều người dùng/runner).
- Lưu **run artefacts**: `parsed/`, `runs/` (constraints/draft/validation/log), `Output/*.docx`.

Với định hướng **web app**, vẫn **không bắt buộc phải có S3** nếu bạn có chỗ lưu khác phù hợp:
- **SharePoint** (qua Microsoft Graph) làm “source of truth” cho tài liệu audit và cũng có thể lưu output.
- Hoặc **Azure Blob/Files** / **NAS nội bộ** / storage chuẩn của org.

Điểm quan trọng không phải S3, mà là cần một **storage layer** cho:
- Input documents (APM/AWP/SOP/PU/Samples/Guidelines)
- Output (DOCX) + run logs (JSON)
- (Tuỳ chọn) parsed cache để chạy nhanh hơn

Kết luận: **S3 không cần thiết** nếu tổ chức đã có storage chuẩn khác (ví dụ SharePoint).

---

### 3) Có trigger từ Portal giống AML use case được không?

**Được.** Mô hình web app/portal thường là:
- Portal UI: user nhập `sample_issues` (form).
- Backend API: tạo job “Run audit”.
- Job runner/worker: tải tài liệu (từ SharePoint hoặc storage), chạy parse/generate, render DOCX.
- Storage: lưu `Output/*.docx` + `runs/*.json` (và có thể `parsed/`).
- Portal hiển thị trạng thái (queued/running/done) và cho **download DOCX**.

Nghĩa là “CLI” trong proposal sẽ được **đóng gói thành worker** (service/job), portal chỉ là lớp trigger + theo dõi + download.

---

### 4) AML use case có dùng Python scripts không?

**Có thể có, nhưng không bắt buộc.** Việc chọn Python hay không phụ thuộc:
- AML platform hiện có (ngôn ngữ/chạy worker/CI/CD).
- Nhu cầu parsing + doc rendering + LLM orchestration (Python đang có hệ sinh thái mạnh: `python-docx`, `pdfplumber`, `openpyxl`).

Nếu AML đã triển khai theo kiểu worker/container và đang dùng Python cho pipeline LLM/documents thì **rất hợp**.
Nếu AML chuẩn hoá stack khác, thì pipeline có thể được port sang stack đó (nhưng effort sẽ tăng).

---

### 5) CLI Tool sẽ host ở đâu? Hay chạy local?

Với **web app**, “CLI tool” nên được hiểu là **pipeline engine** chạy trên server (không phải user tự chạy local).

Các lựa chọn triển khai:
- **Local (POC nhanh)**: auditor chạy trên máy (đúng theo proposal ban đầu).
- **Server/VM nội bộ**: chạy job runner tập trung.
- **Container platform** (khuyến nghị cho portal): chạy worker theo job (scale, audit trail tốt).

Với yêu cầu “user nhập và bấm Run trên portal”, hướng hợp lý là:
- Host backend + worker trong môi trường nội bộ (VM hoặc container)
- Storage dùng SharePoint/Blob/NAS tuỳ chuẩn tổ chức

---

## Gợi ý cập nhật diagram (nếu vẽ lại)

Nếu chuyển sang portal + SharePoint, diagram nên thay đổi các điểm chính:
- “Auditor (terminal)” → “User via Portal (Entra ID SSO)”
- “CLI Tool” → “Web App (API + Job Orchestrator/Worker)”
- “S3 (optional)” → “SharePoint Document Library (source) + Output library (results)”
- Giữ “LLM (Claude)” và “Parsing service” như external dependencies (tuỳ policy)

