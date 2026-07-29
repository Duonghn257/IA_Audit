# 5-Day Solo POC Implementation Plan

## Operation Report Jedi — AI‑Assisted Audit Report Writing

### Document Control

| Item | Details |
| --- | --- |
| Document Title | 5-Day Solo POC Implementation Plan – Operation Report Jedi |
| Author Role | Middle AI Engineer (solo) |
| Related Documents | `FUNCTIONAL_SPECIFICATION.md`, `ARCHITECTURE_PROPOSAL_FINAL.md`, `WORK_BREAKDOWN_STRUCTURE.md` / `.xlsx` |
| Document Purpose | Define a minimal, lite, local end-to-end POC deliverable in 5 working days |

---

## 1. Context

The full Operation Report Jedi plan (`WORK_BREAKDOWN_STRUCTURE.md`) estimates **45.5 working days across 4 sprints** for a production POC — Amazon Bedrock, Azure AI Document Intelligence / LlamaParse, smart section selection, a 3-step prompt chain with self-critique, production-grade guardrails, full DOCX template fidelity, and a 10-project evaluation framework.

A **solo Middle AI Engineer** has only **5 working days** to deliver a working demonstration. This plan narrows the scope ~9× by:

- Running on **one project** only (Lumina Grand — the only complete sample on disk).
- Using **local parsing** libraries (`python-docx`, `pdfplumber`, `openpyxl`) instead of any cloud parsing service.
- Using the **Anthropic API directly** instead of Bedrock — no AWS IAM/VPC/S3 setup.
- Skipping smart section selection, Step 4 LLM self-critique, template fidelity, and batch/eval tooling.
- Hard-coding what would otherwise be engineered modules.

The POC must still be **genuinely end-to-end**: run a single command on the Lumina Grand folder and produce a reviewable DOCX issue log.

---

## 2. Available Data

One complete project on disk: `IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)/` with all 6 artefact folders.

| Folder | Files |
| --- | --- |
| Samples | Issue Log Template v11 Oct 2023 (.docx), approved FY2024 report (.pdf) |
| APM | Lumina Grand APM (.docx) |
| AWP | Lumina Grand AWP (.docx) |
| Process Understanding | PDPA process understanding (.docx), access rights (.xlsx) |
| Process SOP | PDPA CDL Personal Data Policy (.pdf), CDL PDPA Manual (.pdf) |
| Guidelines | Formatting Guidelines v1.1 (.pdf) |
| Output | template.docx |

File types to parse: **.docx, .pdf, .xlsx** — all handled locally by Python libraries.

---

## 3. POC Scope

### 3.1 In-Scope

| Area | Included in 5-day POC |
| --- | --- |
| **Projects** | 1 project (Lumina Grand) |
| **Document Parsing** | Local libraries only — `python-docx`, `pdfplumber`, `openpyxl`. Output: plain text / light Markdown per file. |
| **LLM Provider** | Direct Anthropic API (`anthropic` SDK), model `claude-sonnet-4-5`, API key in `.env`. |
| **Context Assembly** | Naive full-document loading with role tags (`<AWP>`, `<APM>`, `<SOP>`, `<PROCESS_UNDERSTANDING>`, `<GUIDELINES>`, `<SAMPLES>`). Character-budget truncation as fallback. |
| **Prompt Chain** | 2 LLM calls: (1) Constraint extraction from AWP + APM, (2) Issue drafting with role-tagged context. |
| **JSON Schema** | Minimum viable `draft.json`: array of issues `{title, finding, impact, recommendation, evidence_refs[]}`. |
| **Validation** | 2 rule-based checks only — evidence references present; no out-of-scope entity names. Pass/fail to console. |
| **DOCX Output** | `python-docx` basic rendering — title + one table per issue (Title / Finding / Impact / Recommendation). Single font, no template fidelity. |
| **Versioning** | Filename `<Project>_Issue Log v0.x.docx`; auto-bumps version on re-run. |
| **CLI** | Single command: `python main.py --project <path> --issues <issues.json>`. |
| **Auditor Input** | Hand-written `sample_issues.json` seeded from the approved FY2024 report findings. |
| **Quality Test** | One end-to-end run, eyeball comparison to the approved FY2024 report. |

### 3.2 Out-of-Scope (deferred to the full 45.5-day build)

| Area | Deferred |
| --- | --- |
| External parsing services | Azure AI Document Intelligence, LlamaParse |
| Post-parse enrichment | `[GAP]`/`[CONTROL]` tag detection, TOC generation, heading-based section splitting |
| Smart section selection | Method A (keyword-driven) + Method B (LLM-assisted) — unnecessary at 1-project scale |
| Step 4 LLM self-critique | `validation.json`, SCOPE_BREACH / TONE_VIOLATION / UNSUPPORTED_ASSERTION / WEAK_EVIDENCE / HALLUCINATION flags |
| Full CLI | `parse` / `generate` / `status` / `runs` subcommands; no `run_log.json` |
| Caching | Content-hash cache invalidation — POC always re-parses |
| DOCX template fidelity | Matching fonts/styles/heading hierarchy/table grids from `Output/template.docx` |
| Bedrock / AWS | S3, IAM, CloudWatch, cost tracking |
| Multi-project evaluation | 10-project systematic comparison; automated quality scoring |
| Prompt tuning | Single prompt revision per step, no A/B testing |
| Production hardening | Structured logging, unit/integration tests, retries beyond basic rate-limit |
| Auditor UX | Interactive prompts, auditor user guide, feedback capture |

### 3.3 Mapping to the Full WBS

- **Covered (trimmed)**: M0 Project Setup, M1 Document Parsing, M3 Prompt Chain Engine (2/3 steps), M6 DOCX Rendering (minimal), M7 CLI Tool (single entry point).
- **Deferred**: M2 Post-Parse Enrichment, M4 Context Building & Selection (smart selection), M5 Guardrails (LLM pass), the rest of M7, M8 Evaluation & Scale-Out.

---

## 4. Day-by-Day Plan

### Day 1 — Foundation + Parsing (8h)

**Morning (4h)**
- Create Python 3.11+ virtual environment, `requirements.txt`:
  - `anthropic`, `python-docx`, `pdfplumber`, `openpyxl`, `python-dotenv`
- Project layout:
  ```
  src/
    __init__.py
    config.py          # loads .env, ANTHROPIC_API_KEY
    llm.py             # thin Anthropic client wrapper
    parsers.py         # parse_docx, parse_pdf, parse_xlsx, parse_folder
    prompts/
      constraints.py   # Step 1 prompt template
      drafting.py      # Step 3 prompt template
    context.py         # tag + concatenate artefacts, truncate if needed
    validate.py        # 2 rule-based checks
    render.py          # draft.json → DOCX
    versioning.py      # next output filename version
  main.py
  .env.example
  sample_issues.json
  README.md
  ```
- `.env.example` with `ANTHROPIC_API_KEY=`.
- Walking-skeleton `main.py` that prints parsed artefacts to console.

**Afternoon (4h)**
- Implement `parsers.py`:
  - `parse_docx(path) -> str` using `python-docx` — paragraphs + tables → Markdown-ish.
  - `parse_pdf(path) -> str` using `pdfplumber` — text per page, page separators.
  - `parse_xlsx(path) -> str` using `openpyxl` — each sheet as a Markdown table.
  - `parse_folder(root) -> dict[str, list[ParsedDoc]]` — keyed by folder name.
- Sanity run on Lumina Grand; eyeball output for obvious garbage.

**Exit criterion**: `python main.py --project <Lumina path>` prints parsed text grouped by each of the 6 folders.

---

### Day 2 — Context Assembly + Step 1 (Constraint Extraction) (8h)

**Morning (4h)**
- Implement `context.py`:
  - `build_context(parsed)` returns a tagged blob:
    ```
    <AWP>{awp_text}</AWP>
    <APM>{apm_text}</APM>
    <GUIDELINES>{guidelines_text}</GUIDELINES>
    <SAMPLES>{samples_text}</SAMPLES>
    <SOP>{sop_text}</SOP>
    <PROCESS_UNDERSTANDING>{pu_text}</PROCESS_UNDERSTANDING>
    ```
  - Character-budget truncation: if total > ~500k chars, tail-truncate SOP first, then PU; print warning.
- Implement `llm.py`:
  - Wrapper around `anthropic.Anthropic().messages.create(...)` with simple rate-limit retry.
  - `extract_json(text)` — pulls the first ```json``` fenced block or the first balanced `{...}`.

**Afternoon (4h)**
- Implement `prompts/constraints.py` — Step 1 prompt:
  - System: "You are an Internal Audit scope extractor."
  - User: `<AWP>…</AWP>\n<APM>…</APM>` + instruction to return JSON with `audit_scope`, `audited_entities`, `key_risks`, `out_of_scope_items`.
- Run on Lumina Grand, save `output/constraints.json`.
- Inspect; refine prompt if output mis-identifies entities or is too vague.

**Exit criterion**: `constraints.json` produced; scope and entities correctly capture "Lumina Grand / PDPA".

---

### Day 3 — Step 3 Issue Drafting (8h)

**Morning (4h)**
- Implement `prompts/drafting.py` — Step 3 prompt:
  - System: "You are an Internal Audit issue log drafter. Write in the house style shown in `<SAMPLES>`. Stay within `<SCOPE>`. Use only evidence from `<AUDITOR_INPUT>` and `<PROCESS_UNDERSTANDING>`."
  - User: `<SCOPE>{constraints.json}</SCOPE>` + all tagged artefact blobs + `<AUDITOR_INPUT>{issues.json}</AUDITOR_INPUT>` + schema instruction.
  - Output schema (in prompt):
    ```json
    [{"title": "...", "finding": "...", "impact": "...", "recommendation": "...", "evidence_refs": ["..."]}]
    ```
- Prepare `sample_issues.json` by extracting 2–3 gaps from the approved Lumina Grand FY2024 PDF (simulating auditor inputs).

**Afternoon (4h)**
- Wire `main.py`: parse → build context → Step 1 → Step 3 → save `draft.json`.
- Run end-to-end on Lumina Grand.
- Compare draft to approved FY2024 report qualitatively; 1–2 prompt tuning iterations if tone is off.

**Exit criterion**: `draft.json` contains the expected number of issues; audit-report tone; actionable recommendations.

---

### Day 4 — Validation + DOCX Rendering (8h)

**Morning (4h)**
- Implement `validate.py`:
  - `check_evidence_refs(draft)` — every issue has ≥1 `evidence_refs` entry.
  - `check_scope(draft, constraints)` — issue text must not mention entities outside `constraints.audited_entities`. Simple substring check.
  - Return `{"passed": bool, "warnings": [...]}`. Print to console. Non-blocking.

**Afternoon (4h)**
- Implement `render.py`:
  - Blank `Document()` with title paragraph `"<Project> – Issue Log v0.x"`.
  - Per issue: table with 4 rows (Title / Finding / Impact / Recommendation). Single font (Calibri), consistent style.
  - Save to `<project>/Output/<Project>_Issue Log v0.x.docx`.
- Implement `versioning.py`:
  - Scan `Output/` for `*Issue Log v0.*.docx`, regex version, return `v0.(max+1)`.
- Wire into `main.py` after validation.

**Exit criterion**: `python main.py …` on Lumina Grand produces `Lumina Grand_Issue Log v0.1.docx` with all issues as readable tables; re-run yields `v0.2`.

---

### Day 5 — Polish, Demo, Documentation (8h)

**Morning (4h)**
- Harden `main.py`:
  - Clean `argparse` help text.
  - Per-stage progress banners ("Parsing…", "Extracting constraints…", "Drafting…", "Validating…", "Rendering…").
  - Persist intermediate artefacts (`parsed/`, `constraints.json`, `draft.json`, validation log) beside the output DOCX.
- Full re-run on Lumina Grand from a clean state.
- Side-by-side compare the DOCX to the approved FY2024 report. Write `POC_DEMO_NOTES.md`:
  - What the POC matches well (tone, structure, finding selection).
  - Gaps vs. approved report (template fidelity, specific phrasing, missing nuance).
  - Which full-build modules would close each gap (smart selection for long SOPs, LLM self-critique for subtle scope drift, template matching for formatting).

**Afternoon (4h)**
- Write `README.md`:
  - Setup (venv, `pip install -r requirements.txt`, `.env`).
  - Usage (one command line).
  - Input expectations (folder structure, `issues.json` shape).
  - Known limitations (1-project scope, no template fidelity, naive validation).
  - Next steps — point to `WORK_BREAKDOWN_STRUCTURE.md` for the full 45.5-day roadmap.
- **~2h buffer** for bug fixes surfaced during the demo run.
- Commit to a branch; rehearse a ~5-minute stakeholder walkthrough.

**Exit criterion**: One-command run from clean state produces a reviewable DOCX; `README.md` and `POC_DEMO_NOTES.md` exist; demo is rehearsed.

---

## 5. Deliverables

1. `src/` package (~600–900 LOC) with the modules listed above.
2. `main.py` CLI entry point.
3. `sample_issues.json` seeded for Lumina Grand.
4. `output/` per run:
   - `Lumina Grand_Issue Log v0.1.docx` — final generated draft.
   - `parsed/*.md` — per-artefact parsed text.
   - `constraints.json`, `draft.json` — intermediate LLM outputs.
5. `README.md` + `POC_DEMO_NOTES.md`.
6. `requirements.txt`, `.env.example`.

---

## 6. Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Context window blown by large SOPs + PU | Character-budget tail-truncation in `context.py`; warn on truncation. |
| Anthropic API access delayed | Use already-available key in `.env`; fallback path is a 1-file swap to OpenAI / alternate provider in `llm.py`. |
| `pdfplumber` mangles Guidelines PDF layout | ~5-line swap to `PyMuPDF` (`fitz`) in `parse_pdf`. |
| Generated tone diverges from approved report | Day 3 afternoon buffer for prompt tuning; include 1 full approved issue as a few-shot exemplar in the drafting prompt. |
| DOCX rendering consumes a full day | Pre-committed to minimal table-per-issue layout; no template matching. |
| Day-5 buffer eaten by earlier slippage | Drop Day 4 morning validation first — scope/citation checks are nice-to-have for the POC. |

---

## 7. Verification

Success is demonstrated when all of the following hold:

1. `python main.py --project "IA2024-02 CDL Zenith Pte Ltd (Lumina Grand)(Updated)" --issues sample_issues.json` completes without error.
2. A DOCX lands at `<project>/Output/Lumina Grand_Issue Log v0.1.docx`.
3. Opening the DOCX in Word shows 2–3 issue tables with non-empty Finding / Impact / Recommendation rows.
4. Re-running the command produces `v0.2` (does not overwrite `v0.1`).
5. `draft.json` passes both rule-based validation checks.
6. Manual comparison: at least one generated issue corresponds to a finding in the approved FY2024 PDF, even if phrased differently.

---

## 8. Confirmed Decisions

1. **LLM provider**: Anthropic API direct (`anthropic` SDK, `ANTHROPIC_API_KEY` in `.env`). No Bedrock/AWS for POC.
2. **Projects tested**: Lumina Grand only — no batch logic.
3. **Auditor input**: Hand-written `sample_issues.json` seeded from the approved FY2024 report findings.
