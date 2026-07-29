# Functional Specification (POC)

## Operation Report Jedi – AI‑Assisted Audit Report Writing

### Document Control

| Item | Details |
| --- | --- |
| Document Title | Functional Specification – Operation Report Jedi (POC) |
| Initiative | AI Initiative – Report Jedi Proof of Concept |
| Business Owner | Internal Audit (IA) |
| Document Purpose | Define functional requirements for AI-assisted audit report drafting |

## 1. Introduction

### 1.1 Background

Internal Audit currently relies on manual drafting of audit issue logs, which is time‑consuming and can lead to inconsistencies in structure, tone, and terminology across audit reports. As part of the AI Initiative, **Operation Report Jedi** is proposed as a Proof of Concept (POC) to evaluate the use of AI to assist auditors in drafting audit issue reports using approved historical artefacts and standards.

### 1.2 Purpose of This Document

This document defines the **functional scope, capabilities, inputs, outputs, controls, and success criteria** for the Operation Report Jedi POC. It is intended to serve as a reference for Internal Audit, IT, and potential vendors involved in the POC implementation.

## 2. Objectives

The objectives of Operation Report Jedi are to:

- Assist auditors in drafting structured and professional audit issue logs.
- Improve consistency in audit report language, structure, and formatting.
- Reduce manual drafting effort while retaining auditor judgement and accountability.
- Ensure all AI-generated outputs comply with Internal Audit standards, scope, and approved documentation.

## 3. Scope of Proof of Concept

### 3.1 In‑Scope

The POC will cover:

- AI‑assisted drafting of **audit issue logs only**.
- Use of 10 completed audit projects as the training and reference dataset.
- Generation of issue log sections in the desired format, including:
  - Issue / Finding
  - Impact
  - Recommendation
- Application of IA‑approved writing tone, formatting, and structure.

### 3.2 Out‑of‑Scope

The following are explicitly excluded from the POC:

- Performing audit testing or control evaluation.
- Determining audit opinions or assurance conclusions.
- Implementation of a 3-agent AI (Harvester, Sorter, Review Agent) for end-to-end report generation (planned for a later phase).
- Modifying approved audit scope or risk assessment.
- Automated submission or finalisation of audit reports without human review.

## 4. Input Artefacts

The AI solution shall use the approved documents listed below as **reference artefacts** to guide drafting (e.g., tone, structure, and scope alignment). The specific documents provided will vary by audit project, and project-specific samples will be provided to the AI for reference/learning.

| Artefact (by Folders) | Description | Functional Purpose |
| --- | --- | --- |
| Samples | Historical audit issue logs | Provides AI with real-world examples of the final product. It helps the model learn the tone and professional vocabulary. |
| Process Understanding | Process descriptions and control context | Supplies the contextual background. Allows the AI to understand what was audited, the "gaps", "controls", and "lapses". It also contains the **issue identified** by the Auditor and the **evidence**. |
| Guidelines | IA writing and formatting standards | This document contains the formatting requirements (e.g., positive tone for issue title, font requirements, etc) that the AI must follow to meet our standards. |
| Process SOP | Approved process procedures | Serves as the source of truth. Training on these helps AI understand the deviations from established procedures and reference the correct benchmarks. |
| Approved Work Program (AWP) | Audit scope and objectives | Defines the scope and objectives. This ensures the AI stays within the boundaries of the specific audit. |
| Approved Planning Memo (APM) | Risk focus and audit intent | Context on the strategic intent and risk focus. It helps the AI prioritise significant issues by understanding the initial risk assessment and the stakeholder concerns identified at the start. |

## 5. Functional Requirements

### 5.1 Audit Issue Drafting

The system shall:

- Generate audit issue drafts using auditor-provided issue inputs, and by referencing the **Samples** folder formats, the **issue** and **evidence** logged by the auditor in the **Process Understanding** folder, and relevant reference documents in the **APM**, **AWP**, and **Process SOP** folders.
- Populate all mandatory issue log sections as defined in the Issue Log Template.
- Save the generated draft into the Output folder using the naming convention: **\<Project Title\>\_Issue Log v0.1**. For subsequent re-runs, increase the version number (e.g., v0.2, v0.3) and overwrite the prior draft output.
- Apply professional Internal Audit language and format consistently with historical reports, in accordance with standards in the **Guidelines** folder.

### 5.2 Context Awareness

The system shall:

- Reference Process Understanding and SOP documents to contextualise findings.
- Frame issues against approved procedures and controls.
- Avoid introducing assumptions or content not supported by the provided artefacts.

### 5.3 Scope Control

The system shall:

- Restrict outputs to the boundaries defined by the Approved Work Program.
- Reflect risk priorities documented in the Approved Planning Memo.
- Prevent generation of issues outside the approved audit scope.

### 5.4 Formatting and Writing Standards

The system shall:

- Apply IA SOP requirements for formatting and writing style.
- Maintain a constructive and professional tone, including positive issue titles where required.
- Produce drafts suitable for auditor review and refinement.

## 6. User Interaction Flow (POC)

- Auditor completes the audit fieldwork and review (evidence gathering and validation completed) and initiates the report drafting process.
- Auditor provides issue‑specific inputs (e.g. observed gap, evidence summary).
- When triggering the AI to draft, auditor may provide additional context (e.g., expected number of issues/gaps identified). The system shall generate the same number of drafted issues in the output.
- AI generates a draft audit issue log.
- If the auditor re-runs the drafting, the system shall overwrite the previously generated draft and increment the version number (e.g., v0.1 → v0.2 → v0.3) in the Output filename.
- Auditor reviews, edits, and finalises the content.

The AI acts strictly as a **drafting assistant**. Final responsibility and approval remain with the auditor.

### 6.1 Workflow & Responsibilities

## 7. Security, Governance & Compliance

- All documents used are confidential Internal Audit materials.
- Access to training data and outputs shall be restricted to authorised users only.
- AI outputs shall not infer or disclose information beyond the supplied documents.
- NDA clearance and legal approvals are prerequisites for vendor involvement.

## 8. Success Criteria

The POC will be deemed successful if:

- AI‑generated drafts comply with IA structure and formatting standards.
- Auditors experience measurable reduction in drafting effort.
- Output requires refinement rather than full redrafting.
- When tested using completed audits, the AI-generated draft is closely aligned to the corresponding approved audit report (expected outcome) in terms of structure, tone, and key messaging.
- No scope breaches or unsupported assertions are observed.

## 9. Assumptions & Dependencies

- Training documents provided are complete, accurate, and approved.
- Auditor's judgement remains central to report finalisation.

## 10. Future Enhancements (Post‑POC)

The following are not part of the current POC but may be considered subsequently:

- **Harvester Agent** — The agent is responsible for accessing and reading the shared folders for supporting documents.
- **Sorter Agent** — The agent will be responsible for sorting the information to ensure relevance to the portfolio/process audited.
- **Review Agent** — The agent will be responsible as the first reviewer to check for tone and issue angling.
