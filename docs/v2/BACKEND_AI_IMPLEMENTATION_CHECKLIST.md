# Backend and AI UAT Implementation Checklist

> **Scope:** Backend, AI pipeline, persistence, storage, worker and minimal AWS runtime integration only
>
> **Requirements baseline:** [Software Requirements Specification 0.4](SOFTWARE_REQUIREMENTS_SPECIFICATION.md)
>
> **Target release:** 15 September 2026
>
> **Last reviewed:** 12 August 2026

## 1. Scope boundary

This checklist excludes frontend implementation, Entra ID, RBAC, SharePoint,
Textract/OCR, Bedrock, SQS, advanced monitoring, Merge/Split and user-triggered
job cancellation. It assumes the existing Anthropic API and centrally managed
Guidelines/DOCX template will be used for UAT.

Existing POC components that can be reused are FastAPI, SQLAlchemy/PostgreSQL,
Alembic, basic `.docx`/`.pdf`/`.xlsx` parsers, Anthropic integration, DOCX
rendering, project events/SSE and the automated-test foundation. The POC flow
must still be changed from `upload -> run -> DOCX` to three separate commands:

```text
Create project and v0.1 -> Find candidates -> Audit current version
```

## 2. UAT release blockers

### A. Domain model, database and API contract — 4 person-days

- [ ] Define the project, version, issue, job and output state machines.
- [ ] Define one API error format and `allowed_actions` rules for every state.
- [ ] Add database models for upload sessions, source documents and source manifests.
- [ ] Add `project_versions` with project-wide `v0.N` sequence and `base_version_id`.
- [ ] Add issues, typed source references, dispositions, origin and edit revision fields.
- [ ] Add durable jobs, job attempts, progress events, lease/heartbeat and checkpoint fields.
- [ ] Add immutable audit-input snapshots and DOCX output revisions.
- [x] Add current central asset metadata for Guidelines and one DOCX template.
- [ ] Write forward and rollback-safe Alembic migrations.
- [ ] Publish/freeze the OpenAPI contract used by the frontend developer.

**Done when:** a clean PostgreSQL database can migrate to the new schema, and
the API contract represents the complete UAT lifecycle without using the old
single project status as the workflow state.

### B. Folder intake, validation and immutable source — 6 person-days

- [ ] Separate folder upload into a staging/upload session; do not start AI on upload.
- [ ] Preserve safe relative paths and reject absolute paths, traversal and duplicate paths.
- [ ] Enforce a maximum of 20 files and 100,000,000 total bytes server-side.
- [ ] Allow only `.docx`, `.pdf` and `.xlsx`; validate extension, MIME/signature and readability.
- [ ] Reject empty, corrupt, encrypted/password-protected and unsupported files with file-level errors.
- [ ] Resolve the SRS malware-scan gate: scan staged files before promotion or record a Leader-approved UAT exception.
- [ ] Map folders/files to configurable logical roles: `SCOPE`, `RISK_CONTEXT`, `EVIDENCE`, `CRITERIA` and optional project `SAMPLE`.
- [ ] Require readable AWP, APM, evidence and criteria artefacts before discovery is allowed.
- [ ] Return the normalized folder tree, detected role, warnings and blocking errors.
- [ ] Store each original source artefact in private S3 and record hash, size, MIME and object key.
- [ ] Store parsed `.md`/JSON only as derived, rebuildable artefacts; never replace the originals.
- [ ] Promote staging to an immutable project source snapshot.
- [ ] Create the project and `v0.1` atomically after successful confirmation.
- [ ] Ensure uploaded Guidelines/templates cannot override central assets while `Samples/` remains project source.
- [ ] Add expiry/cleanup for abandoned staging sessions without deleting created-project sources.

**Done when:** a valid folder creates exactly one project and `v0.1` without
starting discovery; an invalid folder returns actionable validation errors and
leaves no partial project.

### C. Durable background jobs — 7 person-days

- [ ] Replace `ThreadPoolExecutor` orchestration with a separate PostgreSQL-polling worker.
- [ ] Support two job types: `CANDIDATE_DISCOVERY` and `AUDIT`.
- [ ] Implement atomic job claiming, lease timeout, heartbeat and recovery after worker restart.
- [ ] Persist stage, percentage/step count, message, timestamps, attempt and correlation ID.
- [ ] Add idempotency/concurrency guards so one version cannot start duplicate active jobs of the same type.
- [ ] Make every stage safe to retry from a persisted checkpoint or safely restart from the beginning.
- [ ] Add retry after failure without creating a duplicate project version or corrupt output revision.
- [ ] Record terminal states `SUCCEEDED`, `FAILED` and `INCOMPLETE` with a safe user-facing error.
- [ ] Expose create-job, job-status, event polling/SSE and retry endpoints.
- [ ] Recover or fail expired `RUNNING` jobs during worker startup.
- [ ] Add graceful shutdown so an interrupted attempt becomes recoverable.

**Done when:** the API can restart, the worker can restart, and the user can
leave the page while discovery/Audit continues and later resumes from persisted
state.

### D. AI ingestion and candidate discovery — 16–20 person-days

#### D1. Parsing and provenance

- [ ] Produce a stable `document_id` and `unit_id` for every parsed source unit.
- [ ] Preserve DOCX heading/paragraph/table/cell locations.
- [ ] Preserve PDF page/block/table locations for text-based PDFs; report scanned pages as unsupported in UAT.
- [ ] Preserve XLSX workbook/sheet/cell-range, displayed value and formula metadata.
- [ ] Record parser name/version, source hash and parse warnings on every derived artefact.
- [ ] Cache parsed output by content hash and make parsing deterministic/idempotent.
- [ ] Prevent central Guidelines/templates from being mixed with project evidence provenance; keep project Samples typed as non-evidence context.

#### D2. Scope, criteria and evidence preparation

- [ ] Classify units as `SCOPE`, `RISK_CONTEXT`, `CRITERIA`, `EVIDENCE` or `CONTEXT`.
- [ ] Extract a structured Scope/Control Matrix from AWP/APM and persist it.
- [ ] Extract expected-control statements from criteria sources with exact source references.
- [ ] Extract actual-state/evidence facts, exceptions and missing-evidence signals with exact source references.
- [ ] Reject facts whose document/unit/location cannot be resolved against the immutable source manifest.
- [ ] Track every in-scope objective/control as covered, candidate found, no gap found, insufficient evidence or parse incomplete.

#### D3. Retrieval and prompt orchestration

- [ ] Implement structure/metadata filters plus PostgreSQL full-text retrieval for each control.
- [ ] Retrieve criteria and evidence independently, then assemble a bounded context per control.
- [ ] Add semantic embeddings/pgvector only if the agreed UAT dataset shows full-text retrieval is insufficient.
- [ ] Add token-budget controls, batching and deterministic context ordering.
- [ ] Define versioned structured-output schemas and prompts for scope extraction, evidence extraction, gap detection and reviewer validation.
- [ ] Configure Anthropic timeout, bounded retry/backoff and malformed-JSON recovery.
- [ ] Record model ID, prompt version, central asset IDs/hashes, token usage and run parameters in the manifest.

#### D4. Candidate generation and validation

- [ ] Generate only in-scope candidates that compare an expected state with an observed actual state.
- [ ] Produce `title_hint`, `observed_gap`, `evidence_summary`, typed `source_refs` and optional `risk_category`.
- [ ] Require at least one valid `EVIDENCE` ref and one valid `CRITERIA` ref for every AI candidate.
- [ ] Validate that references belong to the current project snapshot and support the associated claims.
- [ ] Detect unsupported assertions, contradictions, near-duplicates and out-of-scope candidates.
- [ ] Persist candidate validation flags and confidence as review aids, not automatic pass/fail decisions.
- [ ] Persist fact disposition and a minimal coverage matrix; never silently discard extracted facts.
- [ ] Save validated candidates to the selected current version without creating a new version.
- [ ] Mark the discovery job `INCOMPLETE` when required parsing/scope coverage is incomplete.

**Done when:** each visible AI candidate is reproducible from the recorded
model/prompt/source versions and has resolvable Evidence and Criteria citations.

### E. Issue register backend APIs — 4 person-days

- [ ] Add list/get/create/update/disposition endpoints scoped by project version.
- [ ] Store `origin = AI | MANUAL`; never present manual issues as AI-verified.
- [ ] Allow a manual issue to be saved and audited with only `observed_gap` required.
- [ ] Keep `risk_category` optional and editable for both AI and manual issues.
- [ ] Support auditor dispositions such as accepted, rejected, needs evidence and out of scope.
- [ ] Implement optimistic concurrency using a revision/ETag field.
- [ ] Keep an append-only issue change trail with actor label and timestamp for UAT traceability.
- [ ] Mark an existing successful output `STALE` when its version's issue content changes.

**Done when:** issue changes are persistent, conflict-safe and isolated to the
selected version, and manual issues follow their less restrictive evidence
rules.

### F. Audit versions — 4 person-days

- [ ] Add list/get endpoints for all versions of a project.
- [ ] Implement `+ New audit` as a backend command on a selected base version.
- [ ] Allocate the next project-wide version number transactionally (`v0.2`, `v0.3`, ...).
- [ ] Copy issue content and source references from the base version but never copy DOCX outputs.
- [ ] Allow a new version even when the base version has never been audited.
- [ ] Keep old versions editable; edits must not mutate sibling or descendant versions.
- [ ] Return version number, base version, issue state, job state and output availability.

**Done when:** concurrent requests cannot create duplicate version numbers and
every version retains an independent issue workspace and output history.

### G. Audit pipeline and versioned DOCX — 5 person-days

- [ ] Add Audit preflight validation using different rules for AI and manual issues.
- [ ] Freeze an immutable issue/input snapshot when Audit is submitted.
- [ ] Draft only auditor-accepted issues and do not silently add or remove issues.
- [ ] Apply the current centrally managed Guidelines and DOCX template from a frozen job snapshot.
- [ ] Validate source claims, required fields, issue count and document structure before publishing output.
- [ ] Render a DOCX whose filename follows `<Project Name>_Issue Log v0.N.docx`.
- [ ] Attach an immutable output revision to the same current version; Audit must not increment the version.
- [ ] Preserve earlier successful revisions when the same version is audited again.
- [ ] Expose version-specific output listing and private download endpoints.
- [ ] Mark only the new revision current after successful render; a failed re-Audit must not destroy the prior DOCX.

**Done when:** Audit runs in the background from a frozen snapshot, and every
successful DOCX can be downloaded again from the correct project version.

### H. Minimal AWS runtime integration — 3 person-days

- [ ] Implement S3 storage adapter for source, parsed artefacts, job artefacts and DOCX revisions.
- [ ] Use private buckets/objects and short-lived presigned upload/download URLs where appropriate.
- [ ] Run API and worker as separate ECS Fargate services using the same release image or compatible images.
- [ ] Configure RDS PostgreSQL migrations as a controlled deployment step.
- [ ] Load Anthropic key and database credentials from AWS Secrets Manager.
- [ ] Add API/worker readiness checks and verify worker outbound HTTPS access to Anthropic.
- [ ] Verify internal-only ingress through the approved ALB/VPN or IP allowlist.

**Done when:** the full backend workflow runs on AWS without local filesystem
dependency and survives an API or worker task replacement.

### I. Backend/AI self-test and release evidence — 6 person-days

- [ ] Unit-test path/file guards, role mapping, version allocation, state transitions and validators.
- [ ] Add parser fixtures for supported DOCX/PDF/XLSX structures and unsupported scanned/corrupt inputs.
- [ ] Integration-test PostgreSQL migrations, repositories, S3 adapter and worker job claiming/recovery.
- [ ] Contract-test all endpoints and error payloads against the frozen OpenAPI schema.
- [ ] E2E-test `upload -> create v0.1 -> discovery -> issue edit/manual issue -> Audit -> DOCX download`.
- [ ] Test `+ New audit` before the base version has any DOCX.
- [ ] Test retry after Anthropic timeout, malformed response, worker restart and render failure.
- [ ] Test edits after output, stale status, re-Audit and preservation of earlier DOCX revisions.
- [ ] Build a small auditor-approved golden dataset containing clear gaps, no-gap controls and insufficient-evidence cases.
- [ ] Manually review candidate citation correctness, false positives, false negatives and DOCX usability on that dataset.
- [ ] Verify no live Anthropic call occurs in the default automated test suite.
- [ ] Record release smoke-test evidence and confirm there are no open P0/P1 backend defects.

**Done when:** one clean AWS run and the required failure/retry scenarios pass
using release-candidate images and migrations.

## 3. Recommended implementation order

```text
A Domain/API/schema
  -> B Intake + v0.1
  -> C Durable jobs
  -> D AI discovery
  -> E Issue APIs
  -> G Audit + DOCX
  -> I End-to-end release verification

F Versioning can start after A and run in parallel with D.
H AWS adapters can start after A/C contracts stabilize and must finish before I.
```

## 4. Remaining effort summary

| Work package | Remaining estimate |
|---|---:|
| Domain/database/API contract | 4 person-days |
| Folder intake and immutable source | 6 person-days |
| Durable jobs | 7 person-days |
| AI ingestion and discovery | 16–20 person-days |
| Issue register APIs | 4 person-days |
| Audit versions | 4 person-days |
| Audit and DOCX revisions | 5 person-days |
| Minimal AWS runtime integration | 3 person-days |
| Backend/AI self-test and release evidence | 6 person-days |
| **Total remaining Backend/AI effort** | **55–59 person-days** |

This estimate assumes reuse of the current POC parser, Anthropic client and
DOCX renderer. It does not include frontend work or a separate QA resource.
The critical path is the durable job foundation followed by the AI discovery
pipeline and its real-artefact tuning.

## 5. Deferred follow-up checklist

- [ ] Entra ID authentication, user ownership and RBAC.
- [ ] SharePoint import/export.
- [ ] Textract or another OCR path for scanned PDFs.
- [ ] Bedrock model integration.
- [ ] SQS/DLQ instead of PostgreSQL job polling.
- [ ] User-triggered job cancellation.
- [ ] Merge/Split issue workflow.
- [ ] Formal automated AI quality threshold and regression dashboard.
- [ ] Advanced observability, alerting and security scanning.
