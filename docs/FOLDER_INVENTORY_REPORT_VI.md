# Báo cáo thống kê cây thư mục — IA Audit Report use case

**Phạm vi**: Toàn bộ thư mục gốc `IA Audit Report use case/` (đã loại trừ `.DS_Store`, file tạm Word `~$*`, `.~*`).  
**Thời điểm quét**: snapshot tại thời điểm tạo báo cáo (cấu trúc có thể thay đổi khi thêm/xóa file).

---

## 1) Tổng quan thống kê

| Chỉ số | Giá trị |
|--------|---------|
| **Số thư mục gốc (level 1)** | 1 thư mục con chính + file ở root |
| **Số thư mục con (toàn bộ)** | 8 (bao gồm các cấp dưới của project Lumina Grand) |
| **Tổng số file** | **14** (bao gồm báo cáo inventory này) |
| **Tổng dung lượng (ước tính)** | ~**8,9 MB** (không tính chính xác byte sau khi thêm `.md`) |

### Phân bố theo loại file (extension)

| Loại | Số file | Ghi chú |
|------|---------|---------|
| `.docx` | 6 | Spec, APM, AWP, template output, Process Understanding, Issue Log template |
| `.pdf` | 4 | Guidelines, 2× Process SOP, 1× báo cáo mẫu trong Samples |
| `.md` | 3 | Nghiên cứu, phân tích yêu cầu, báo cáo thống kê folder (do team tạo) |
| `.xlsx` | 1 | Dữ liệu bảng trong Process Understanding |

---

## 2) Sơ đồ cây thư mục (text)

```
IA Audit Report use case/
├── Functional Specification - Operation Report Jedi.docx
├── PROJECT_RESEARCH_VI.md
├── REQUIREMENTS_ANALYSIS_VI.md
├── FOLDER_INVENTORY_REPORT_VI.md          ← báo cáo thống kê folder/file
│
└── IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/
    ├── APM/
    │   └── Lumina Grand_2. APM (8 Mar) (V3).docx
    ├── AWP/
    │   └── Lumina Grand_5. AWP (8 Mar) (V3).docx
    ├── Guidelines/
    │   └── Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf
    ├── Output/
    │   └── template.docx
    ├── Process SOP/
    │   ├── CDL PDPA Manual - Final v1.pdf
    │   └── PDPA CDL Personal Data Policy Aug 2018_FINAL.pdf
    ├── Process Understanding/
    │   ├── PD_Roles_AccessRights_22Mar2024.xlsx
    │   └── Process Understanding - Lumina Grand PDPA.docx
    └── Samples/
        ├── 1. Issue Log Template_version 11 Oct 2023.docx
        └── FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf
```

> **Lưu ý**: Trên đĩa có thể còn file tạm Word (ví dụ `~$ocess Understanding...`) — không liệt kê trong báo cáo này vì thường là lock file, không phải nội dung dự án.

---

## 3) Chi tiết từng folder

### 3.1 Thư mục gốc — `IA Audit Report use case/`

Chứa **functional spec** của POC và **tài liệu markdown** phục vụ team; đồng thời là điểm vào tới **bộ artefacts mẫu** một project audit (Lumina Grand).

| File | Kích thước (bytes) | Vai trò ngắn gọn |
|------|-------------------|------------------|
| `Functional Specification - Operation Report Jedi.docx` | 102 937 | Định nghĩa POC Operation Report Jedi: mục tiêu, phạm vi, input/output, success criteria |
| `PROJECT_RESEARCH_VI.md` | 11 595 | Ghi chép nghiên cứu tài liệu (tiếng Việt) |
| `REQUIREMENTS_ANALYSIS_VI.md` | 9 102 | Phân tích yêu cầu dự án (tiếng Việt) |
| `FOLDER_INVENTORY_REPORT_VI.md` | (tùy phiên bản) | Báo cáo thống kê folder/file (tài liệu này) |

---

### 3.2 `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/`

**Ý nghĩa**: Đây là **một project audit mẫu** (mã IA2024-02), bố trí artefacts theo cấu trúc mà spec Operation Report Jedi mong đợi (APM, AWP, Guidelines, Process SOP, Process Understanding, Samples, Output).

Các **subfolder** bên dưới tương ứng với từng “nhóm vai trò” của tài liệu (xem từng mục).

---

### 3.3 `.../APM/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `Lumina Grand_2. APM (8 Mar) (V3).docx` | 403 546 | **Approved Planning Memo**: bối cảnh dự án, stakeholder, lo ngại, thời gian fieldwork, trọng tâm rủi ro, thông tin đặc thù project — dùng để **ưu tiên** và **ngữ cảnh** khi draft issue (không thay thế ranh giới scope trong AWP). |

---

### 3.4 `.../AWP/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `Lumina Grand_5. AWP (8 Mar) (V3).docx` | 101 426 | **Approved Work Program**: scope, objectives, sub-process, work steps, phân bổ man-days — là **chuẩn ranh giới** để hệ thống **không** sinh issue ngoài phạm vi đã duyệt. |

---

### 3.5 `.../Guidelines/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf` | 1 872 699 | Chuẩn **format & proofreading** cho issue log (font, spacing, bảng exception, tone, cross-reference, footer CONFIDENTIAL, v.v.). |

---

### 3.6 `.../Output/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `template.docx` | 94 258 | **Template đầu ra** (ví dụ: bảng Issues / Audit Risk Level / Page và phần chi tiết issue). Theo spec POC, draft issue log được lưu vào Output với tên dạng `<Project Title>_Issue Log v0.x`. |

---

### 3.7 `.../Process SOP/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `CDL PDPA Manual - Final v1.pdf` | 1 737 487 | Manual PDPA nội bộ CDL — **benchmark “should-be”** khi audit/khi viết issue liên quan PDPA. |
| `PDPA CDL Personal Data Policy Aug 2018_FINAL.pdf` | 211 080 | Personal Data Policy (dạng policy tổng quát) — bổ sung **chuẩn thu thập/sử dụng/disclose** personal data. |

**Tóm lại folder này**: Tài liệu **chính sách/quy định đã ban hành** để đối chiếu với thực tế ghi trong Process Understanding.

---

### 3.8 `.../Process Understanding/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `Process Understanding - Lumina Grand PDPA.docx` | 1 628 750 | Workpaper **walkthrough** PDPA: objectives, procedures, mô tả kênh thu thập dữ liệu, control/gap, bằng chứng — **nguồn chính** để viết Finding/Impact kèm căn cứ. |
| `PD_Roles_AccessRights_22Mar2024.xlsx` | 36 535 | Dữ liệu dạng **bảng** (ví dụ roles/access) — thường dùng cho kiểm tra quyền hoặc làm exception listing trong issue. |

---

### 3.9 `.../Samples/`

| File | Kích thước (bytes) | Ý nghĩa |
|------|-------------------|---------|
| `1. Issue Log Template_version 11 Oct 2023.docx` | 108 526 | **Issue Log Template** chuẩn IA — định nghĩa các section bắt buộc khi sinh draft. |
| `FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf` | 1 072 033 | Báo cáo audit **đã phát hành** (mẫu) — dùng để học **tone/structure** và đối chiếu chất lượng POC. |

---

## 4) Bảng tra cứu nhanh: Folder → vai trò trong Operation Report Jedi

| Folder | Vai trò trong POC |
|--------|-------------------|
| **APM** | Ngữ cảnh & trọng tâm rủi ro (planning memo) |
| **AWP** | Ranh giới scope & objectives (work program) |
| **Guidelines** | Chuẩn viết & định dạng issue log |
| **Process SOP** | Benchmark chính sách/SOP (“should-be”) |
| **Process Understanding** | Thực tế + evidence (“as-is”) |
| **Samples** | Template đầu ra + ví dụ báo cáo đã duyệt |
| **Output** | Nơi đặt template/ghi file draft theo version |

---

## 5) Phụ lục — Danh sách đầy đủ file (đường dẫn tương đối)

1. `Functional Specification - Operation Report Jedi.docx`
2. `PROJECT_RESEARCH_VI.md`
3. `REQUIREMENTS_ANALYSIS_VI.md`
4. `FOLDER_INVENTORY_REPORT_VI.md`
5. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/APM/Lumina Grand_2. APM (8 Mar) (V3).docx`
6. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/AWP/Lumina Grand_5. AWP (8 Mar) (V3).docx`
7. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Guidelines/Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).pdf`
8. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Output/template.docx`
9. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process SOP/CDL PDPA Manual - Final v1.pdf`
10. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process SOP/PDPA CDL Personal Data Policy Aug 2018_FINAL.pdf`
11. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process Understanding/PD_Roles_AccessRights_22Mar2024.xlsx`
12. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Process Understanding/Process Understanding - Lumina Grand PDPA.docx`
13. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Samples/1. Issue Log Template_version 11 Oct 2023.docx`
14. `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/Samples/FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf`

---

*Tài liệu được tạo để team onboard nhanh: thống kê + ý nghĩa từng folder/file trong phạm vi use case hiện có.*
