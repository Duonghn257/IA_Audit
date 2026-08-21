# UAT Release Estimation Plan

> **Product:** Operation Report Jedi
>
> **Plan version:** 1.2
>
> **Plan date:** 10 August 2026
>
> **Target release date:** 15 September 2026
>
> **Requirements baseline:** [Software Requirements Specification 0.4](SOFTWARE_REQUIREMENTS_SPECIFICATION.md)
>
> **Delivery model:** Two developers; developer-led testing with no dedicated QA resource

## 1. Planning basis

The period from 10 August to 15 September 2026 contains **27 working days**,
including the release date. The project has two developers and no dedicated
tester. Each developer must implement features and test the other developer's
completed work before it is merged.

The current POC already has local upload, FastAPI, Vue, PostgreSQL, progress
events, an AI drafting pipeline and DOCX rendering. The UAT scope still requires
a material workflow redesign: staged upload, `v0.1` creation, candidate
discovery, candidate review, manual issues, audit-version handling, current
version DOCX output, retry/recovery and internal-UAT deployment hardening.

## 2. Effort estimate

| Work package | Estimate |
|---|---:|
| Data model, API contracts and database migrations | 4 person-days |
| Project intake: staging, validation, 20-file/100-MB limits, central assets, immutable source and `v0.1` | 12 person-days |
| Background discovery/Audit job foundation, progress, retry and recovery | 10 person-days |
| Evidence/Criteria candidate discovery and validation | 12 person-days |
| Candidate register, manual issue entry and issue review UI | 10 person-days |
| **+ New audit** versioning and version navigation | 8 person-days |
| Audit current version, DOCX output revisions, stale state and download | 8 person-days |
| Internal-access deployment hardening, secrets and protected download | 3 person-days |
| Developer-led integration testing, browser testing, UAT support and release preparation | 11 person-days |
| **Base effort** | **78 person-days** |
| **Contingency (15%)** | **12 person-days** |
| **Planning total** | **90 person-days** |

Two developers have a maximum theoretical capacity of **54 person-days** over
27 working days. Actual delivery capacity is lower because both developers must
self-test, fix defects, deploy and support UAT. Therefore, the full 90
person-day scope cannot be treated as a safe commitment for 15 September without
additional capacity, scope reduction, or schedule extension.

## 3. Date-based delivery plan

| Date | Developer 1 | Developer 2 | Self-test / expected outcome |
|---|---|---|---|
| **10–12 Aug** | Finalise backend data model, job/version states and API contracts. | Finalise UAT screens and API integration contract. | Cross-review contracts; confirm internal access boundary, central template and scope freeze. |
| **13–18 Aug** | Implement upload staging, server validation, 20-file/100-MB limits, immutable source and automatic `v0.1`. | Implement upload wizard, validation result, folder tree and project/version display. | Test valid/invalid folders, limits and `v0.1` creation. |
| **19–22 Aug** | Implement separate background job model, durable events, retry skeleton and recovery behavior. | Update project workspace for discovery status, progress and reconnect states. | Developer cross-test reload/reconnect, failed job and retry behavior. |
| **24–28 Aug** | Implement Evidence/Criteria discovery flow, candidate schema and validation rules. | Implement Candidate Issue Register, candidate details, edit/reject and manual issue entry. | Test AI candidate refs, manual issue with only observed gap, and issue-save conflicts. |
| **31 Aug–4 Sep** | Implement **+ New audit**, `v0.N` sequence, base-version copy and version persistence. | Implement version list, selected-version view and **+ New audit** UI. | Test `v0.1` on project creation; create `v0.2` before `v0.1` has DOCX. |
| **7–9 Sep** | Implement Audit using current version, frozen input, DOCX output revision, stale state and versioned filename. | Implement Audit action, output status, stale indicator and version-specific download. | Test audit does not increase version; filename contains current version; re-Audit preserves output history. |
| **8–10 Sep** | Configure internal-only deployment, secrets and download endpoint. | Complete deployment/error states and release self-test support. | Verify corporate VPN/IP restriction, outbound Anthropic access and private-output download. |
| **10–11 Sep** | Fix backend/integration defects; prepare migration, backup and rollback steps. | Complete browser happy-path and negative-path self-tests; fix UI defects. | Release Candidate 1: upload → discovery → review → Audit → download. |
| **14 Sep** | Support final UAT, fix release-blocking defects and deploy final release candidate. | Run regression on the final candidate and verify downloads/versions. | Go/no-go decision; no open P0/P1 defects. |
| **15 Sep** | Deploy and smoke-test release. | Smoke-test release and support handover. | Release completed. |

## 4. Mandatory dependencies

| Required by | Dependency | Impact if not available |
|---|---|---|
| **18 Aug** | Corporate VPN/approved IP range and internal UAT HTTPS endpoint | Internal-access deployment cannot be completed safely. |
| **12 Aug** | Approved central Guidelines and DOCX template | DOCX output cannot be finalised against the required standard. |
| **21 Aug** | Auditor/Product Owner availability for candidate and DOCX feedback | Defects and AI quality issues move into the final release week. |
| **28 Aug** | Retention decision for staging, source files and DOCX output | Cleanup/operational behavior remains incomplete. |

## 5. Release conditions

- Valid upload creates `v0.1` and does not automatically start discovery.
- Folder limits enforce `.docx`, `.pdf`, `.xlsx`, maximum 20 files and 100 MB.
- Every AI candidate has Evidence and Criteria; manual issues may contain only
  `observed_gap`.
- **+ New audit** is the only action that creates `v0.2+`.
- Audit creates DOCX for the current version and does not increase its version.
- DOCX filename contains the current version.
- Failed discovery/Audit can be retried without duplicate versions or outputs.
- Portal is reachable only from the approved internal network; no app login/RBAC is expected in this UAT.
- Both developers complete cross-testing of the end-to-end browser workflow.
- No open P0 or P1 defects at release.

## 6. Delivery assessment

The table above is the best-case schedule for two developers working in parallel
and testing each other's work. It shows the intended order of delivery, but the
full UAT scope is larger than the available two-person capacity before 15
September.

To keep the release date, the Leader should decide one of the following by 12
August:

1. Add capacity.
2. Reduce/defer items from the estimated scope.
3. Accept a later release date.

Without one of these decisions, the 15 September release should be considered a
high-risk target rather than a firm delivery commitment.
