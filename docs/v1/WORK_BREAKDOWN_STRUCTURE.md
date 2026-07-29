# Work Breakdown Structure - Operation Report Jedi
## Detailed Production Timeline and Phase Plan

| Item | Detail |
|------|--------|
| **Document Title** | Work Breakdown Structure - Operation Report Jedi Production Build |
| **Version** | 1.1 |
| **Date** | 2026-05-25 |
| **Status** | Draft - detailed phase WBS |
| **Reference** | Architecture Proposal v1.0; production architecture diagram |
| **Deadline** | Production pilot-ready by **15 September 2026** |
| **Architecture** | Portal + SharePoint project folder + AWS-hosted API/orchestrator/worker |

---

## 1. Planning Assumptions

| Assumption | Detail |
|---|---|
| Start date | 25 May 2026 |
| Target completion | 15 September 2026 |
| Delivery window | Approximately 16 weeks |
| UAT timing | UAT starts immediately after workflow completion in Phase 3 |
| Observability timing | Basic logs are included during build; enhanced logs/tracing/alarms can be implemented after UAT starts |
| Evidence input | Users upload files to SharePoint and specify the project folder in Portal |
| Runtime | AWS-hosted web app, orchestrator, and worker containers |
| LLM | AWS Bedrock Claude |
| Parsing | AWS Textract where OCR/layout extraction is required |
| Output | Draft DOCX output package, plus JSON artifacts for auditability |

---

## 2. Timeline to Mid-September

Target: complete pilot-ready production build by **Tuesday, 15 September 2026**.

| Phase | Dates | Duration | Primary Goal | Exit Criteria |
|---|---:|---:|---|---|
| **Phase 0 - Mobilize and Confirm** | 25 May - 5 Jun | 2 weeks | Confirm scope, access model, environments, and delivery controls | Architecture/access decisions are approved and build can start |
| **Phase 1 - Foundation Build** | 8 Jun - 26 Jun | 3 weeks | Build Portal intake, SharePoint read path, and AWS baseline | User can submit a SharePoint folder and backend can list/read files |
| **Phase 2 - Processing Core** | 29 Jun - 24 Jul | 4 weeks | Build ingestion, parsing, cache, and Bedrock prompt chain | One pilot project can generate `constraints.json`, `draft.json`, and `validation.json` |
| **Phase 3 - Workflow Complete** | 27 Jul - 14 Aug | 3 weeks | Complete output rendering, artifact download, and core controls | End-to-end workflow works from Portal submission to DOCX download |
| **Phase 4 - UAT and Pilot Validation** | 17 Aug - 4 Sep | 3 weeks | Run UAT immediately after workflow completion | IA users validate outputs and critical workflow issues are fixed |
| **Phase 5 - Operations Hardening and Final Sign-off** | 7 Sep - 15 Sep | 1.5 weeks | Add enhanced logs/tracing/alarms, close release checklist | Pilot-ready sign-off achieved by 15 Sep |

---

## 3. Detailed Phase WBS

### Phase 0 - Mobilize and Confirm

**Dates:** 25 May - 5 Jun  
**Goal:** Confirm the decisions and access paths that can block the build.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P0-01 | Confirm production scope | Review architecture proposal with IA, Portal, Cloud, Security, and SharePoint owners. Confirm what is in scope for pilot: SharePoint folder input, issue input, generation, validation, DOCX output, download. | Approved scope note exists. Out-of-scope items are explicitly listed, especially in-app approval workflow, advanced dashboards, and PDF output if deferred. |
| P0-02 | Confirm delivery timeline | Walk through the 25 May - 15 Sep timeline and agree milestone owners. Identify blackout dates, review dates, and UAT participants. | Milestone dates are accepted by project owner. UAT participants and pilot audit projects are named. |
| P0-03 | Decide ECS vs EKS path | Ask Cloud Platform whether CDL mandates EKS. If not, default to ECS/Fargate for faster delivery and lower operational overhead. | Written decision exists. Infrastructure module can proceed without waiting for platform debate. |
| P0-04 | Confirm Microsoft Graph permission model | Review delegated user permission vs application permission with Security and SharePoint admins. Decide how the worker is allowed to read project folders. | Graph permission model is approved or has a dated approval path. Required Azure app registration/scopes are listed. |
| P0-05 | Confirm AWS environment path | Identify AWS account, VPC/subnet model, secrets management, Bedrock model access, Textract access, RDS/S3/ElastiCache ownership. | AWS account/environment request is submitted or approved. Bedrock Claude access path is confirmed. |
| P0-06 | Confirm data handling controls | Define how source files, parsed text, generated outputs, logs, and metadata are stored and retained. | Draft security checklist exists covering S3 encryption, RDS encryption, IAM, log redaction, and retention. |
| P0-07 | Define pilot test dataset | Select 1-3 audit projects for build validation and UAT. Confirm SharePoint folder structure and expected files. | Pilot folders are available or scheduled. IA confirms expected documents: APM, AWP, SOP, Process Understanding, Guidelines, Samples, evidence. |

**Phase 0 exit gate:** architecture/access decisions confirmed, pilot folders identified, and build teams can start without major access blockers.

---

### Phase 1 - Foundation Build

**Dates:** 8 Jun - 26 Jun  
**Goal:** Build the minimum technical foundation: Portal intake, API, SharePoint read, and AWS baseline.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P1-01 | Build Portal folder submission screen | Add Portal UI fields for SharePoint folder URL/path, project name, audit entity, optional notes, and issue input upload/manual entry. | User can enter a SharePoint folder and submit. Required-field validation works. Invalid URL/path shows clear error. |
| P1-02 | Define backend API contract | Define API endpoints for create job, validate folder, submit issue input, get job status, and download output. | API contract is documented with request/response examples. Portal and backend teams agree on payload shape. |
| P1-03 | Create API Gateway route skeleton | Configure Amazon API Gateway routes to backend service. Add request IDs and basic auth integration through Portal context. | Portal can call a test backend endpoint through API Gateway and receive a response. |
| P1-04 | Provision backend runtime | Deploy initial web app API container on ECS/Fargate or EKS. Configure environment variables and secrets access. | Health endpoint returns OK from deployed environment. Deployment can be repeated from CI/CD or documented deployment command. |
| P1-05 | Provision core storage | Create S3 bucket(s), RDS instance/schema, and ElastiCache instance/serverless cache according to approved environment design. | Backend can write/read a test artifact in S3, insert/read a test row in RDS, and write/read a test key in ElastiCache. |
| P1-06 | Implement Graph folder resolver | Convert SharePoint folder URL/path into site/drive/folder IDs using Microsoft Graph. | Given a valid pilot folder, backend resolves it to Graph IDs. Invalid or unauthorized folder returns controlled error. |
| P1-07 | Implement Graph file listing | List files and folders under the specified project folder. Capture file name, path, ID, size, modified time, web URL, and version/hash if available. | Backend returns a file manifest for pilot folder. Manifest matches SharePoint folder contents. |
| P1-08 | Implement Graph file read/download | Read file content stream for supported files. Store temporary working copy or stream to parser. | Backend can fetch at least one PDF, DOCX, XLSX, and image from pilot folder. File byte size matches SharePoint source. |
| P1-09 | Create case/job metadata schema | Define RDS tables for case, job, source folder, source files, artifact references, job events, and validation summary. | Creating a job writes case/job/source folder rows. Status can be queried by job ID. |
| P1-10 | Add basic job state handling | Store submitted/running/completed/failed states in RDS and short-lived progress in ElastiCache. | A test job moves through submitted -> running -> completed. Portal can poll status. |

**Phase 1 exit gate:** user can submit a SharePoint folder from Portal, backend validates access, lists/reads files through Graph, and records job metadata in AWS.

---

### Phase 2 - Processing Core

**Dates:** 29 Jun - 24 Jul  
**Goal:** Convert SharePoint files into parsed context and generate draft/validation JSON through Bedrock.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P2-01 | Implement document classification | Classify files by folder name, filename pattern, metadata, or manual mapping: APM, AWP, Guidelines, SOP, Process Understanding, Samples, Evidence. | Manifest shows correct document class for pilot files. Unknown files are flagged for user mapping instead of silently ignored. |
| P2-02 | Implement file version/hash cache | Store source file ID, modified time, version/eTag/hash, and parsed artifact reference. Skip parsing unchanged files. | Re-running the same folder does not reparse unchanged files. Changing one file causes only that file to reparse. |
| P2-03 | Implement native text extraction | Extract text from DOCX/XLSX/text PDFs where possible before using OCR. Normalize into Markdown/text with page/sheet references where feasible. | Sample DOCX/XLSX content is extracted and stored in S3 parsed cache. Tables are readable enough for prompt use. |
| P2-04 | Integrate AWS Textract | Send scanned PDFs/images or OCR-required files to Textract. Normalize returned text/tables/layout into parsed output. | Scanned sample PDF/image produces text output. Textract page count is recorded. Parser errors are captured in job status. |
| P2-05 | Build parsed artifact schema | Save parsed content and metadata to S3: document class, source reference, hash/version, page count, token estimate, parse status. | Each parsed file has content artifact and metadata artifact. Metadata can be queried by job ID/source file ID. |
| P2-06 | Implement section splitting and token counting | Split parsed text by headings/pages/sheets. Estimate tokens per section for context budgeting. | For pilot files, section list exists and token counts are plausible. Very large sections are flagged. |
| P2-07 | Build Bedrock Claude client | Implement model invocation wrapper with retries, timeout handling, model ID, prompt version, and token usage capture. | A test prompt returns a response. Token usage/model ID/prompt version are written to run metadata. |
| P2-08 | Implement constraint extraction | Assemble APM/AWP context and prompt Claude to extract scope, entities, risks, exclusions, and constraints into `constraints.json`. | `constraints.json` is valid JSON, includes audited entity/scope/risk fields, and is reviewed against pilot APM/AWP. |
| P2-09 | Implement context assembly | Select relevant Guidelines, SOP, Process Understanding, Samples, and evidence sections based on issue input and constraints. | For sample issues, selected sections are relevant and token budget is respected. Context package can be inspected. |
| P2-10 | Implement issue drafting | Prompt Claude to draft issue log content with citations and structured fields. | `draft.json` validates against schema and includes finding, impact, recommendation, evidence references, and issue title. |
| P2-11 | Implement validation/self-critique | Prompt Claude and run deterministic checks for scope, unsupported assertions, missing citations, and incomplete fields. | `validation.json` contains warnings/errors with severity and location. A seeded unsupported claim is flagged. |
| P2-12 | Save run artifacts | Store `constraints.json`, `draft.json`, `validation.json`, context manifest, and token/cost metadata in S3/RDS. | Job detail page or backend query can retrieve all artifacts for a completed generation run. |

**Phase 2 exit gate:** for at least one pilot project, backend can read SharePoint files, parse/cache them, call Bedrock, and produce valid `constraints.json`, `draft.json`, and `validation.json`.

---

### Phase 3 - Workflow Complete

**Dates:** 27 Jul - 14 Aug  
**Goal:** Complete the user workflow from Portal submission to downloadable DOCX output, with core security and audit controls.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P3-01 | Build DOCX renderer | Convert `draft.json` into the required IA issue log DOCX structure using the approved template/style rules. | Generated DOCX opens in Word, has correct issue structure, headings, tables, and readable formatting. |
| P3-02 | Implement output versioning | Name outputs by project and version. Increment version on re-run. Preserve prior outputs. | Running the same case twice creates v0.1 then v0.2 or agreed version pattern. Prior output remains downloadable. |
| P3-03 | Build output package | Package DOCX plus JSON artifacts and run metadata. Store package or artifact set in S3. | S3 contains DOCX, `constraints.json`, `draft.json`, `validation.json`, and run metadata for each completed job. |
| P3-04 | Implement Portal job status | Show submitted/running/completed/failed states, step progress, and validation warning count. | User can see job progress without refreshing backend manually. Failed job shows reason and next action. |
| P3-05 | Implement Portal download flow | Return authorized download link or stream output package through backend. | Only authorized user/project users can download. Downloaded DOCX matches S3 artifact. |
| P3-06 | Implement validation summary display | Show validation warnings/errors in Portal so user can decide whether to review/re-run. | Portal displays validation severity, issue location, and message from `validation.json`. |
| P3-07 | Add core audit trail | Persist source folder, source files, versions/hashes, job state changes, artifact references, model ID, prompt version, and validation status. | For a completed job, reviewer can reconstruct what files and model/prompt version produced the output. |
| P3-08 | Apply core security controls | Enforce least-privilege IAM, S3/RDS encryption, Portal authorization checks, and basic log redaction. | Security checklist for pilot is reviewed. No raw document body or prompt text appears in standard application logs. |
| P3-09 | End-to-end workflow test | Run from Portal folder submission through SharePoint read, parsing, Bedrock generation, DOCX render, and download. | One pilot project completes end-to-end. Output package is downloadable and artifacts are queryable. |
| P3-10 | Freeze UAT build candidate | Tag or record the build/config/prompt version to be used for UAT. | UAT build candidate is identified. Open defects are triaged as blocking/non-blocking. |

**Phase 3 exit gate:** complete workflow is available for UAT: SharePoint folder in -> generated issue log package out.

---

### Phase 4 - UAT and Pilot Validation

**Dates:** 17 Aug - 4 Sep  
**Goal:** Start UAT immediately after workflow completion. Validate business usefulness, output quality, and user workflow before enhanced observability work.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P4-01 | Prepare UAT script | Create step-by-step UAT instructions: create/select SharePoint folder, enter folder path, enter issue inputs, run job, review validation summary, download DOCX, provide feedback. | UAT script is reviewed by IA lead. Testers can follow it without developer assistance. |
| P4-02 | Prepare UAT data | Select pilot SharePoint folders and issue inputs. Confirm documents are complete and access is granted to test users. | Each UAT tester can access the assigned SharePoint folder and Portal flow. Missing files are resolved before testing. |
| P4-03 | Run UAT session 1 | IA users run the workflow with support team observing. Capture usability, access, job execution, and output quality issues. | UAT evidence captured: screenshots, job IDs, generated files, feedback notes, defect list. |
| P4-04 | Evaluate draft quality | IA SMEs compare generated issue logs against expectations for scope, tone, structure, citations, and unsupported claims. | Quality scorecard completed for each pilot run. Critical content gaps are logged. |
| P4-05 | Fix blocking workflow defects | Prioritize issues that block folder access, job completion, output download, or basic DOCX readability. | Blocking defects are fixed and retested. Job can complete without manual developer intervention. |
| P4-06 | Tune prompts and validation | Adjust prompts/rules for recurring quality problems found during UAT, such as verbosity, citation gaps, or wrong issue grouping. | Before/after output comparison shows improvement. Prompt version is updated in metadata. |
| P4-07 | Run UAT session 2 | Re-run UAT with fixed workflow and tuned prompts. Include at least one re-run on the same project to test cache/version behavior. | UAT testers confirm workflow is usable. Re-run generates new version and reuses unchanged parsed cache. |
| P4-08 | Confirm pilot acceptance | Review UAT results with IA Product Owner and agree whether remaining defects are acceptable for pilot. | Pilot acceptance checklist is signed off or has only agreed non-blocking issues. |

**Phase 4 exit gate:** IA users have tested the end-to-end workflow and accepted it for pilot readiness, subject to final hardening and release checklist.

---

### Phase 5 - Operations Hardening and Final Sign-off

**Dates:** 7 Sep - 15 Sep  
**Goal:** Implement enhanced logging/tracing/alarms after UAT starts, close final release items, and achieve pilot-ready sign-off.

| ID | Task | How We Do It | How To Check It Works / Done |
|---|---|---|---|
| P5-01 | Add structured operational logs | Standardize log fields: request ID, job ID, case ID, user hash, step name, status, duration, error code. Avoid raw document text. | Logs can trace one job across API and worker. Confidential document content is not logged. |
| P5-02 | Add trace correlation | Propagate correlation ID from Portal/API Gateway through API, worker, Graph calls, Textract calls, Bedrock calls, and artifact writes. | Given a job ID, support can find related API and worker events. |
| P5-03 | Add CloudWatch metrics | Emit metrics for submitted jobs, completed jobs, failed jobs, average duration, Textract pages, Bedrock tokens, validation warning count. | Metrics appear in CloudWatch for test runs and have expected values. |
| P5-04 | Add basic alarms | Configure alarms for failed jobs, repeated Graph failures, repeated Bedrock failures, high job duration, and worker backlog if queue is used. | Simulated failure triggers alarm or test notification path. |
| P5-05 | Create operations runbook | Document how to investigate failed jobs, Graph access errors, Textract errors, Bedrock errors, stuck jobs, and output download problems. | Support engineer can follow runbook to diagnose a known failed test job. |
| P5-06 | Complete release checklist | Confirm UAT sign-off, security checklist, known issues, rollback plan, environment config, prompt version, model ID, and retention settings. | Release checklist is complete with owner/date for each item. |
| P5-07 | Final stakeholder review | Present pilot status, UAT results, known limitations, cost/usage notes, and rollout plan. | Stakeholders approve pilot-ready state by 15 Sep. |

**Phase 5 exit gate:** pilot-ready sign-off achieved by **15 September 2026**. Enhanced observability is in place at a practical first-production level; deeper dashboards can continue post-pilot.

---

## 4. Milestone Plan

| Milestone | Target Date | Exit Criteria |
|---|---:|---|
| **MS1 - Architecture and Access Confirmed** | 5 Jun 2026 | Architecture approved; ECS/EKS direction agreed; Graph permission model agreed; AWS environment path confirmed |
| **MS2 - SharePoint Folder Intake Working** | 19 Jun 2026 | Portal/API accepts folder URL/path; backend validates access and lists files through Microsoft Graph |
| **MS3 - AWS Runtime Baseline Ready** | 26 Jun 2026 | API Gateway, runtime, S3, RDS, ElastiCache, IAM baseline, and config/secrets path are available |
| **MS4 - Parsing Pipeline Working** | 17 Jul 2026 | SharePoint files are classified, parsed/cached, and stored with metadata |
| **MS5 - AI Draft Generation Working** | 24 Jul 2026 | Bedrock chain produces constraints, draft, and validation for one pilot project |
| **MS6 - Workflow Complete / UAT Candidate Ready** | 14 Aug 2026 | Portal-to-DOCX workflow works end-to-end and UAT build candidate is frozen |
| **MS7 - UAT Round 1 Complete** | 21 Aug 2026 | First IA UAT session completed; defects and output quality feedback logged |
| **MS8 - UAT Acceptance Complete** | 4 Sep 2026 | Blocking UAT defects fixed; IA accepts pilot workflow |
| **MS9 - Pilot-Ready Sign-off** | 15 Sep 2026 | Operations hardening complete enough for pilot; release checklist closed |

---

## 5. Critical Path

The critical path to meet the 15 September deadline is:

1. Confirm Graph permission model and AWS runtime decision by 5 Jun.
2. Build SharePoint folder read path by 19 Jun.
3. Complete AWS runtime baseline by 26 Jun.
4. Complete parsing/cache pipeline by 17 Jul.
5. Complete Bedrock draft generation by 24 Jul.
6. Complete end-to-end Portal-to-DOCX workflow by 14 Aug.
7. Start UAT on 17 Aug.
8. Complete UAT acceptance by 4 Sep.
9. Complete operations hardening and sign-off by 15 Sep.

Enhanced logs/tracing are not on the path to start UAT, but they are on the path to pilot-ready operational sign-off.

---

## 6. Responsibility Map

| Area | Primary Owner | Supporting Teams |
|---|---|---|
| Business requirements and acceptance | IA Product Owner | Audit users, project sponsor |
| Portal workflow | Portal/Application Team | IA Product Owner |
| SharePoint/Graph access | Microsoft 365 / SharePoint Admin | Security, Application Team |
| AWS infrastructure | Cloud Platform Team | Security, Application Team |
| AI prompt and report quality | AI/Application Team | IA SMEs |
| Security and governance | Security / Risk | Cloud Platform, IA, Application Team |
| UAT coordination | Project Delivery Lead | IA pilot users, Application Team |
| Operations readiness | Application Team | Cloud Platform, Support, Security |

---

## 7. Risks to Timeline

| Risk | Timeline Impact | Mitigation |
|---|---|---|
| Graph permission approval delayed | Blocks SharePoint folder read path | Start permission design in Phase 0; prepare delegated and app-permission options |
| ECS vs EKS decision delayed | Blocks infrastructure baseline | Set decision deadline at MS1; default to ECS/Fargate if no platform mandate |
| AWS account/VPC setup delayed | Blocks API/worker deployment | Start environment request immediately in Phase 0 |
| Bedrock model access delayed | Blocks prompt pipeline | Request Bedrock Claude access in Phase 0 and verify with test prompt in Phase 2 |
| Textract quality gaps | Delays parsing acceptance | Test scanned PDFs early; add manual extraction fallback for pilot |
| DOCX template fidelity takes longer than expected | Delays UAT candidate | Freeze minimum viable DOCX structure by MS6; defer cosmetic refinements |
| UAT feedback requires prompt changes | Compresses final hardening window | Run IA review on early draft outputs during Phase 2 and Phase 3, before formal UAT |
| Observability takes longer than expected | Risks operational sign-off but not UAT start | Keep Phase 5 scope to practical first-production logs/metrics/alarms; defer dashboards |

---

## 8. Definition of Done

| Level | Definition |
|---|---|
| Phase task done | Task output exists, is reviewed by owning team, and has objective evidence such as screenshot, job ID, artifact, test result, or approved document |
| Phase done | All phase exit criteria are met and open defects are classified as blocking/non-blocking |
| UAT done | IA users complete agreed UAT scripts, output quality is reviewed, and blocking defects are resolved |
| Pilot-ready done | UAT accepted, operational minimum controls are in place, release checklist is closed, and stakeholders sign off by 15 Sep |

---

*End of Work Breakdown Structure - Operation Report Jedi v1.1*
