# Work Breakdown Structure (WBS)

## Operation Report Jedi — POC

| Item | Detail |
|------|--------|
| **Document Title** | Work Breakdown Structure — Operation Report Jedi (POC) |
| **Date** | 2026-04-16 |
| **Status** | Draft |
| **Reference** | Functional Specification v1.0; Architecture Proposal v1.0 |

---

## WBS Overview

The WBS is organised into **8 modules** aligned with the architecture proposal's 4-sprint roadmap:

| Module | Description | Sprint |
|--------|-------------|--------|
| **M0** | Project Setup & Environment | Sprint 1 |
| **M1** | Document Parsing Pipeline | Sprint 1 |
| **M2** | Post-Parse Enrichment | Sprint 1 |
| **M3** | Prompt Chain Engine | Sprint 2 |
| **M4** | Context Building & Selection | Sprint 2 |
| **M5** | Guardrails & Validation | Sprint 3 |
| **M6** | DOCX Rendering | Sprint 3 |
| **M7** | CLI Tool & UX | Sprint 3 |
| **M8** | Evaluation & Scale-Out | Sprint 4 |

---

## Detailed WBS

| Task No. | Module | Task Name | Task Detail | Est. Time |
|----------|--------|-----------|-------------|-----------|
| | | | | |
| **M0** | **Project Setup & Environment** | | | |
| M0-01 | Project Setup | Initialise Python project structure | Set up Python project with Poetry/pip, define folder layout (`src/`, `tests/`, `config/`), create `pyproject.toml` or `setup.py`, configure linting (ruff/flake8) and formatting (black). | 0.5 day |
| M0-02 | Project Setup | Configure AWS credentials and Bedrock access | Set up IAM role/user for Bedrock API access, configure AWS CLI profiles, verify Bedrock model access (Claude Sonnet), create `.env` template for environment variables. | 0.5 day |
| M0-03 | Project Setup | Set up external parsing service account | Register for Azure AI Document Intelligence (or LlamaParse), obtain API keys, verify connectivity, document rate limits and pricing tier. | 0.5 day |
| M0-04 | Project Setup | Define project folder convention and config schema | Define the expected project folder structure (`APM/`, `AWP/`, `Guidelines/`, `Process SOP/`, `Process Understanding/`, `Samples/`, `Output/`, `parsed/`, `runs/`). Create a `project_config.json` schema that maps folder paths to artefact types. | 0.5 day |
| M0-05 | Project Setup | Set up sample project dataset (Lumina Grand) | Organise the first sample audit project (Lumina Grand) into the defined folder structure. Verify all artefact types are present (APM, AWP, Guidelines, SOP, PU, Samples). Create a checklist for completeness. | 0.5 day |
| M0-06 | Project Setup | Create logging and configuration framework | Implement a configuration loader (reads `project_config.json` + CLI args + env vars). Set up Python logging with structured JSON output. Define log levels and output destinations (console + file). | 0.5 day |
| | | | | |
| **M1** | **Document Parsing Pipeline** | | | |
| M1-01 | Document Parsing | Build file discovery module | Implement a module that scans a project folder, identifies all documents (DOCX/PDF/XLSX), maps each to its `folder_type` (APM/AWP/Guidelines/SOP/PU/Samples) based on parent folder, and returns a manifest of files to parse. | 0.5 day |
| M1-02 | Document Parsing | Implement file hashing and cache check | For each discovered file, compute SHA-256 hash. Compare against existing `parsed/<doc_id>.meta.json` hashes. Build a list of files that need (re-)parsing vs. files already cached. | 0.5 day |
| M1-03 | Document Parsing | Integrate Azure AI Document Intelligence API client | Write a client wrapper for the Azure AI Document Intelligence Layout API. Handle authentication, request construction, response parsing, error handling, and retry logic. Support DOCX, PDF, and XLSX inputs. | 1 day |
| M1-04 | Document Parsing | Implement LlamaParse API client (fallback) | Write an alternative client wrapper for LlamaParse API as a fallback parsing option. Same interface as Azure AI client so they are interchangeable via config. | 0.5 day |
| M1-05 | Document Parsing | Build parsing output normaliser | Convert the raw parsing service response (Azure AI or LlamaParse) into a normalised Markdown format. Preserve table structures as Markdown tables, maintain heading hierarchy, and retain page number references. | 1 day |
| M1-06 | Document Parsing | Implement parsed file writer | Save normalised output to `parsed/<doc_id>.md` and create the initial `parsed/<doc_id>.meta.json` with: `doc_id`, `source_path`, `source_hash`, `folder_type`, `total_pages`, `total_tokens`. | 0.5 day |
| M1-07 | Document Parsing | Build parse orchestrator | Orchestrate the full parse flow: discover files -> check cache -> send unparsed files to parsing service -> normalise output -> save to `parsed/`. Handle parallel/sequential parsing. Report progress. | 0.5 day |
| M1-08 | Document Parsing | Test parsing pipeline with Lumina Grand artefacts | Run the full parsing pipeline on all Lumina Grand documents. Manually review parsed output for accuracy: check table preservation, heading structure, page references. Fix issues found. | 1 day |
| | | | | |
| **M2** | **Post-Parse Enrichment** | | | |
| M2-01 | Post-Parse Enrichment | Implement tag detection module | Build regex-based scanner to detect IA-specific tags in parsed text: `[CONTROL]`, `[GAP]`, `[LAPSE]`, `[ENHANCEMENT]`. Annotate detected tags in the corresponding `meta.json` sections. | 0.5 day |
| M2-02 | Post-Parse Enrichment | Implement section splitter | Split parsed Markdown by heading hierarchy (H1, H2, H3). For each section, record: `id`, `heading`, `level`, `pages` (start-end), `token_count`. Store as `sections[]` array in `meta.json`. | 1 day |
| M2-03 | Post-Parse Enrichment | Build section index (TOC) generator | Generate a structured table of contents per document from the section split data. This TOC is the key index used for smart section selection during generation (Section 6 of architecture). | 0.5 day |
| M2-04 | Post-Parse Enrichment | Implement token counter | Build a token counting utility (using `tiktoken` or similar) that accurately estimates token counts for each section. Store counts in `meta.json` to enable token budget management during context assembly. | 0.5 day |
| M2-05 | Post-Parse Enrichment | Wire enrichment into parse pipeline | Integrate tag detection, section splitting, TOC generation, and token counting into the parse orchestrator so they run automatically after each document is parsed. | 0.5 day |
| M2-06 | Post-Parse Enrichment | Validate enrichment output for Lumina Grand | Review all `meta.json` files for Lumina Grand project. Verify sections are correctly split, tags are detected, token counts are reasonable. Fix edge cases (e.g., documents with unusual heading structures). | 0.5 day |
| | | | | |
| **M3** | **Prompt Chain Engine** | | | |
| M3-01 | Prompt Chain | Build Bedrock LLM client wrapper | Create a client module that calls Amazon Bedrock's `InvokeModel` API for Claude. Handle: model selection, request construction, response parsing, token usage tracking, error handling, retries with exponential backoff. | 1 day |
| M3-02 | Prompt Chain | Implement JSON output parser | Build a robust JSON extraction module that parses LLM responses into structured Python objects. Handle: JSON embedded in markdown code fences, partial JSON recovery, schema validation against expected output shapes. | 0.5 day |
| M3-03 | Prompt Chain | Design and implement Step 1 prompt (Constraint Extraction) | Write the system prompt and user prompt template for constraint extraction from AWP + APM. Define the `constraints.json` output schema. Implement the prompt assembly function that injects full AWP and APM text. | 1 day |
| M3-04 | Prompt Chain | Implement Step 1 execution and output handling | Wire Step 1 prompt to the Bedrock client. Parse response into `constraints.json`. Save to `runs/<timestamp>/constraints.json`. Implement caching: re-use existing constraints if AWP/APM hashes are unchanged. | 0.5 day |
| M3-05 | Prompt Chain | Design and implement Step 3 prompt (Issue Drafting) | Write the system prompt and user prompt template for issue drafting. Define the `draft.json` output schema (including `issues[]`, `citations[]`, `tables[]`). Implement role-tagged context injection (`[GUIDELINES]`, `[PROCESS SOP]`, etc.). | 1 day |
| M3-06 | Prompt Chain | Implement Step 3 execution — single-issue mode | Wire Step 3 prompt to the Bedrock client for a single issue. Parse response into the `draft.json` schema. Track token usage. Handle issues where context exceeds budget (truncation strategy). | 0.5 day |
| M3-07 | Prompt Chain | Implement Step 3 execution — multi-issue batching | Extend Step 3 to handle multiple issues: decide whether to batch all issues in one call (if total context fits) or iterate per issue. Merge individual results into a single `draft.json`. | 0.5 day |
| M3-08 | Prompt Chain | Design and implement Step 4 prompt (Validation/Self-Critique) | Write the system prompt and user prompt template for the review/validation step. Define the `validation.json` output schema (with `flags[]`: type, location, detail, suggestion). Inject `draft.json`, `constraints.json`, and Guidelines text. | 1 day |
| M3-09 | Prompt Chain | Implement Step 4 execution and output handling | Wire Step 4 prompt to the Bedrock client. Parse response into `validation.json`. Save to `runs/<timestamp>/validation.json`. | 0.5 day |
| M3-10 | Prompt Chain | Build prompt chain orchestrator | Create the main orchestrator that sequences: Step 1 (constraints) -> Step 2+3 (context + drafting) -> Step 4 (validation). Handle inter-step data passing, error recovery (retry on LLM failure), and progress reporting. | 0.5 day |
| M3-11 | Prompt Chain | Test prompt chain end-to-end with Lumina Grand | Run the full 3-step chain on the Lumina Grand dataset with sample auditor inputs. Review output quality: check citations, scope compliance, tone, completeness. Iterate on prompts based on results. | 1 day |
| | | | | |
| **M4** | **Context Building & Selection** | | | |
| M4-01 | Context Building | Implement TOC-based keyword matching (Method A) | Build the keyword extraction module: extract keywords from auditor input (`in_scope_process`, `observed_gap`). Match keywords against section headings and tags in each document's `meta.json`. Rank sections by relevance (keyword hit count). | 1 day |
| M4-02 | Context Building | Implement token budget manager | Build a module that, given a list of ranked sections and a token budget (default ~30K per doc type), selects sections that fit within budget. Prioritise higher-ranked sections. Return selected section IDs and total token count. | 0.5 day |
| M4-03 | Context Building | Implement LLM-assisted section selection (Method B — fallback) | Build the fallback selection method: send the TOC list (headings + IDs only, ~2K tokens) to LLM with a short prompt asking which sections are relevant. Parse response to get section IDs. Trigger when Method A returns ambiguous results (too many or too few matches). | 0.5 day |
| M4-04 | Context Building | Build context assembly module for Process SOP | Implement the specific selection strategy for Process SOP documents: smart section selection via TOC match by issue topic. Load only matching sections (~10-15 pages). Tag loaded content with `[PROCESS SOP — §X]` role markers. | 0.5 day |
| M4-05 | Context Building | Build context assembly module for Process Understanding | Implement the specific selection strategy for PU documents: match by issue topic + filter for `[GAP]`/`[CONTROL]`/`[LAPSE]`/`[ENHANCEMENT]` tagged sections. Tag loaded content with `[PROCESS UNDERSTANDING]` role markers. | 0.5 day |
| M4-06 | Context Building | Build context assembly for full-load artefacts | Implement loading strategy for artefacts that are loaded in full: AWP (full — Step 1), APM (full — Step 1), Guidelines (full — Step 3), Samples template (full — Step 3). Add role tags to each. | 0.5 day |
| M4-07 | Context Building | Build sample issue matcher for approved reports | Implement keyword-based matching to select 1-2 example issues from the Samples (approved reports) folder that are most similar to the current issue being drafted. Use issue titles and topics for matching. | 0.5 day |
| M4-08 | Context Building | Build master context assembler | Create the top-level module that, given an issue from `issues.json` and the parsed project data, assembles the complete context for the Step 3 drafting prompt: selected SOP sections + selected PU sections + full Guidelines + matched Samples + constraints. Report total token count. | 0.5 day |
| M4-09 | Context Building | Test context assembly with Lumina Grand | Run context assembly for 2-3 sample issues on Lumina Grand. Verify: correct sections selected, token budget respected, role tags applied, no irrelevant sections included. Compare selected sections against what a human would choose. | 1 day |
| | | | | |
| **M5** | **Guardrails & Validation** | | | |
| M5-01 | Guardrails | Implement rule-based scope check | Build a code-based check that verifies each drafted issue's `in_scope_process` exists in `constraints.json`'s `in_scope_processes`. Flag `SCOPE_BREACH` if not found. | 0.5 day |
| M5-02 | Guardrails | Implement rule-based citation coverage check | For each issue in `draft.json`, verify: (a) at least 1 citation exists from PU or SOP; (b) no issue has citations only from Samples/Guidelines (flag `WEAK_EVIDENCE`); (c) flag `UNSUPPORTED_ASSERTION` if Finding or Impact has zero citations. | 0.5 day |
| M5-03 | Guardrails | Implement rule-based completeness check | Verify each issue has non-empty: `finding`, `possible_impact`, `recommendations[]`. Flag `INCOMPLETE_SECTION` for any missing required fields. Check `title` is present and non-empty. | 0.5 day |
| M5-04 | Guardrails | Implement rule-based format check | Check cross-reference patterns (e.g., "Refer to Table X for details"), table numbering consistency (e.g., `A1-1`, `A1-2`), issue code format, and structural alignment with template. Flag `FORMAT_ISSUE` on violations. | 0.5 day |
| M5-05 | Guardrails | Build validation aggregator | Combine results from LLM-based validation (Step 4 — `validation.json`) and rule-based checks (M5-01 to M5-04). Merge all flags into a single `validation.json` with `overall_status` (PASS / PASS_WITH_WARNINGS / FAIL). Deduplicate overlapping flags. | 0.5 day |
| M5-06 | Guardrails | Implement configurable flag behaviour | Add configuration option to control behaviour on ERROR-level flags: (a) always generate DOCX with warnings (default), or (b) block DOCX generation on `SCOPE_BREACH`. Read from `project_config.json`. | 0.5 day |
| | | | | |
| **M6** | **DOCX Rendering** | | | |
| M6-01 | DOCX Rendering | Analyse template DOCX structure | Open the provided `template.docx` in python-docx, map out all styles (heading styles, table styles, paragraph styles, fonts), identify placeholders, document the expected structure for issue index table and issue detail sections. | 0.5 day |
| M6-02 | DOCX Rendering | Build DOCX template loader and style manager | Implement loading `template.docx` as the base document. Create a style helper that applies IA formatting rules: Arial 10pt body, Arial 9pt tables, grey-shaded table headers, bold header cells. | 0.5 day |
| M6-03 | DOCX Rendering | Implement Issue Index table renderer | Populate the Issue Index table from `draft.json`'s `issue_index[]` array. Columns: Issue Code, Issue Title, Risk Level, Page Reference. Apply table styling. | 0.5 day |
| M6-04 | DOCX Rendering | Implement Issue Detail section renderer | For each issue in `draft.json`, render the detail section: S/N, Finding (prose), Possible Impact (prose), Recommendations (numbered list), Management Comments (blank), Action Plan (blank), Responsibility (blank), Target Date (blank). | 1 day |
| M6-05 | DOCX Rendering | Implement exception table renderer | Render `tables[]` from `draft.json` into Word tables within each issue's detail section. Apply column headers, row data, and "Refer to Table X" cross-reference text. | 0.5 day |
| M6-06 | DOCX Rendering | Implement document footer and metadata | Add "CONFIDENTIAL" footer to all pages. Set document properties (title, author). Add section breaks between issues if supported by python-docx. | 0.5 day |
| M6-07 | DOCX Rendering | Implement version management | Scan `Output/` folder for existing `*_Issue Log v*.docx` files. Extract highest version number. Increment to next version (e.g., v0.1 -> v0.2). Save new file with correct naming convention: `<Project Title>_Issue Log v0.x.docx`. | 0.5 day |
| M6-08 | DOCX Rendering | Test DOCX output with Lumina Grand | Generate a full DOCX output for Lumina Grand. Open in Microsoft Word. Verify: formatting, table structure, cross-references, issue index, page layout. Document any formatting gaps between generated output and expected format. | 1 day |
| | | | | |
| **M7** | **CLI Tool & UX** | | | |
| M7-01 | CLI Tool | Build CLI framework with `parse` command | Set up CLI framework (click or argparse). Implement `report-jedi parse --project <path>` command that triggers the full parsing pipeline (M1). Add `--verbose` flag for detailed output. Show progress indicators. | 0.5 day |
| M7-02 | CLI Tool | Build CLI `generate` command | Implement `report-jedi generate --project <path> --input <issues.json>` command that triggers: cache check -> prompt chain -> DOCX rendering. Add optional flags: `--model`, `--skip-validation`, `--verbose`. | 0.5 day |
| M7-03 | CLI Tool | Build CLI `status` command | Implement `report-jedi status --project <path>` that displays the last run's summary: issues generated, flags raised, output file path, token usage, duration. Read from `runs/<latest>/run_log.json`. | 0.5 day |
| M7-04 | CLI Tool | Build CLI `runs` command | Implement `report-jedi runs --project <path>` that lists all historical runs for a project: timestamp, version, issue count, flag count, cost. Read from `runs/*/run_log.json`. | 0.5 day |
| M7-05 | CLI Tool | Design and implement `issues.json` input schema | Define the JSON schema for auditor input file. Implement schema validation with clear error messages. Document each field (`issue_hint_title`, `observed_gap`, `evidence_summary`, `preferred_risk_level`, `in_scope_process`). Create a sample `issues.json` for Lumina Grand. | 0.5 day |
| M7-06 | CLI Tool | Implement CLI output formatting | Build the terminal output module: step-by-step progress display (`[1/5] Parsing documents...`), coloured flag display (yellow for WARNING, red for ERROR), final summary with output path and stats. | 0.5 day |
| M7-07 | CLI Tool | Implement run log writer | After each generation run, write `run_log.json` to `runs/<timestamp>/` containing: run_id, project_id, timestamp, model, input_file hash, documents_used (with hashes), token_usage per step, total_tokens, estimated_cost, issues_generated, flags, output_version, output_path, duration_seconds. | 0.5 day |
| M7-08 | CLI Tool | Implement error handling and user-friendly messages | Add comprehensive error handling across the CLI: missing project folder, missing artefacts, parsing service errors, Bedrock API errors, invalid `issues.json`, permission errors. Provide actionable error messages. | 0.5 day |
| | | | | |
| **M8** | **Evaluation & Scale-Out** | | | |
| M8-01 | Evaluation | Onboard remaining 9 audit projects — batch 1 (3 projects) | Organise 3 additional audit projects into the defined folder structure. Run parsing pipeline. Verify parsed output quality. Fix any parsing issues specific to these projects' document formats. | 1 day |
| M8-02 | Evaluation | Onboard remaining 9 audit projects — batch 2 (3 projects) | Organise 3 more audit projects. Parse and verify. Address any new edge cases in document formats or structures not seen in batch 1. | 1 day |
| M8-03 | Evaluation | Onboard remaining 9 audit projects — batch 3 (3 projects) | Organise final 3 audit projects. Parse and verify. Complete all 10 projects in the system. | 1 day |
| M8-04 | Evaluation | Generate drafts for all 10 projects | Run `report-jedi generate` for all 10 projects with appropriate auditor inputs. Collect all outputs (`draft.json`, `validation.json`, DOCX files, `run_log.json`). | 1 day |
| M8-05 | Evaluation | Build evaluation comparison checklist | Create a structured checklist/scorecard for comparing AI-generated drafts against approved reports. Criteria: structure alignment, tone consistency, citation accuracy, scope compliance, key messaging coverage. | 0.5 day |
| M8-06 | Evaluation | Evaluate drafts — batch 1 (projects 1-5) | Perform side-by-side comparison of AI drafts vs. approved reports for 5 projects. Score each issue on the evaluation checklist. Document discrepancies and areas for improvement. | 1 day |
| M8-07 | Evaluation | Evaluate drafts — batch 2 (projects 6-10) | Perform side-by-side comparison for remaining 5 projects. Score and document. | 1 day |
| M8-08 | Evaluation | Aggregate metrics and compile evaluation report | Aggregate across all 10 projects: citation coverage rate, flag rates by type, quality scores, token usage patterns, cost per project. Compute averages and identify trends. | 0.5 day |
| M8-09 | Evaluation | Prompt tuning iteration — round 1 | Based on evaluation findings, adjust prompts (Step 1, 3, 4) to address systematic issues found across projects (e.g., tone drift, citation gaps, formatting inconsistencies). Re-run 2-3 projects to verify improvements. | 1 day |
| M8-10 | Evaluation | Prompt tuning iteration — round 2 | Second round of prompt refinement based on round 1 results. Focus on edge cases and remaining quality gaps. Re-run and verify. | 1 day |
| M8-11 | Evaluation | Create auditor user guide | Write a concise user guide for auditors: how to prepare the project folder, how to write `issues.json`, how to run `parse` and `generate` commands, how to interpret flags and warnings, how to iterate on drafts. | 0.5 day |
| M8-12 | Evaluation | Compile final POC evaluation report | Write the POC evaluation report: executive summary, methodology, results across 10 projects, quality metrics, time-saving estimates, cost analysis, recommendations for production phase, identified limitations. | 1 day |

---

## Summary

| Module | Task Count | Total Est. Time |
|--------|-----------|-----------------|
| M0 — Project Setup & Environment | 6 | 3 days |
| M1 — Document Parsing Pipeline | 8 | 5 days |
| M2 — Post-Parse Enrichment | 6 | 3.5 days |
| M3 — Prompt Chain Engine | 11 | 7.5 days |
| M4 — Context Building & Selection | 9 | 5 days |
| M5 — Guardrails & Validation | 6 | 3 days |
| M6 — DOCX Rendering | 8 | 4.5 days |
| M7 — CLI Tool & UX | 8 | 4 days |
| M8 — Evaluation & Scale-Out | 12 | 10 days |
| **Total** | **74 tasks** | **45.5 days** |

---

## Sprint Mapping

| Sprint | Weeks | Modules | Est. Days |
|--------|-------|---------|-----------|
| Sprint 1 — Document Parsing & Project Setup | Week 1-2 | M0, M1, M2 | 11.5 days |
| Sprint 2 — Prompt Chain & Draft Generation | Week 3-4 | M3, M4 | 12.5 days |
| Sprint 3 — DOCX Rendering & Guardrails | Week 5-6 | M5, M6, M7 | 11.5 days |
| Sprint 4 — Evaluation & Scale-Out | Week 7-8 | M8 | 10 days |

---

*End of Work Breakdown Structure — Operation Report Jedi (POC)*
