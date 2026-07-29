# End-to-End POC Design — Operation Report Jedi

## Document Control

| Item | Details |
| --- | --- |
| Title | End-to-End POC Design – Operation Report Jedi |
| Date | 2026-04-18 |
| Author | Middle AI Engineer (solo) |
| Supersedes | Parts of `docs/POC_5DAY_IMPLEMENTATION_PLAN.md` — where this spec and the 5-day plan disagree, this spec wins |
| Related | `docs/FUNCTIONAL_SPECIFICATION.md` (scope authority), `docs/ARCHITECTURE_PROPOSAL_FINAL.md` (long-term), `CLAUDE.md` (project guardrails) |

---

## 1. Summary

Operation Report Jedi is a Proof of Concept that drafts Internal Audit issue logs from approved historical artefacts and auditor-seeded inputs. This spec defines the end-to-end POC: a single-command Python CLI that parses one audit project's folder, runs a 4-step LLM chain (constraints → drafting → self-critique → styling), and emits a reviewable DOCX alongside intermediate JSON artefacts.

**Target dataset:** `data/lumina_grand/` (PDPA audit, FY2024).
**LLM:** Anthropic API direct, model `claude-sonnet-4-5`.
**Parsing:** Local libraries only — `python-docx`, `pdfplumber`, `openpyxl`.
**Runtime:** single-user, single-project, always re-parse.
**Quality gate:** manual side-by-side comparison of generated DOCX against the held-out approved FY2024 report.

## 2. Scope

### In-scope
- One project (Lumina Grand) end-to-end
- 6-folder artefact convention: APM, AWP, Guidelines, Process SOP, Process Understanding, Samples
- 4-step LLM chain: constraint extraction → drafting → self-critique → styling
- Rule-based + LLM-based validation (both non-blocking, informational)
- DOCX rendering with template-palette fidelity (summary index + per-issue multi-section tables + review-procedures appendix)
- Versioned output under `data/<project>/Output/v0.N/`

### Out-of-scope (deferred to full build — see `CLAUDE.md` §"What is deliberately out of scope")
- AWS Bedrock, Azure Document Intelligence, LlamaParse
- Smart section selection, caching, prompt A/B infrastructure
- Multi-project batch, automated quality scoring
- Harvester / Sorter / Review Agent architecture
- Any subcommand beyond the single entry point

---

## 3. Architecture

### 3.1 Style

Procedural pipeline. Pure-ish functions in `src/` modules. `main.py` wires stages top-to-bottom. JSON files are the handoff format between stages; each stage can be re-executed in isolation by reading its predecessor's JSON artefact.

### 3.2 Module layout

```
ia_audit_report/
├── main.py                     # CLI entry; wires the 8 stages
├── sample_issues.json          # hand-seeded auditor input (Lumina Grand)
├── requirements.txt
├── .env / .env.example
├── src/
│   ├── __init__.py
│   ├── config.py               # loads .env
│   ├── llm.py                  # Anthropic wrapper + JSON extraction + retry
│   ├── parsers.py              # parse_docx / pdf / xlsx / folder + persist_parsed
│   ├── context.py              # role-tag + concatenate (+ hold-out list, truncation)
│   ├── template_inspector.py   # extract palette/fonts/page-setup from template + sample DOCX
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── constraints.py      # Step 1 prompt + caller
│   │   ├── drafting.py         # Step 2 prompt + caller
│   │   ├── critique.py         # Step 3 prompt + caller
│   │   └── styling.py          # Step 4 prompt + caller + DEFAULT_STYLE_SPEC + normalise_style_spec
│   ├── validate.py             # 2 rule-based checks; merges with LLM critique
│   ├── render.py               # draft.json + style_spec.json → DOCX
│   └── versioning.py           # next v0.N in Output/
└── docs/ …                     # spec, functional, WBS, plan
```

### 3.3 Pipeline stages

Each stage's outputs land in `data/<project>/Output/v0.N/`.

| # | Stage | Input | Output |
|---|---|---|---|
| 1 | **Parse** | `data/<project>/` folders | `parsed/<folder>/<file>.md` |
| 2 | **Build context** | parsed docs | in-memory role-tagged blobs |
| 3 | **Extract constraints** (LLM 1) | `<AWP>`, `<APM>` | `constraints.json` |
| 4 | **Draft issues** (LLM 2) | tagged context + `<SCOPE>` + `<AUDITOR_INPUT>` | `draft.json` |
| 5 | **Self-critique** (LLM 3) | `<DRAFT>` + evidence + `<SCOPE>` + `<GUIDELINES>` | `validation.json` (llm_critique section) |
| 6 | **Produce style spec** (LLM 4) | `<GUIDELINES>` + `<TEMPLATE_ANALYSIS>` (from `template_inspector`) + `<DRAFT>` | `style_spec.json` |
| 7 | **Rule-based validate** | `draft.json`, `constraints.json` | `validation.json` (rule_based section merged); `run.log` summary line |
| 8 | **Render** | `draft.json` + `style_spec.json` + `constraints.review_procedures` | `<Project>_Issue Log v0.N.docx` |

Stage 6 is tolerant: if the styling LLM call fails, the pipeline logs a warning and continues with `DEFAULT_STYLE_SPEC` merged with any template-derived colors. `normalise_style_spec` always applies the template's observed palette as ground-truth overrides over the LLM output.

The template inspector reads `Output/template.docx` plus every `Samples/*.docx` (excluding Word lock files `~$*.docx`). Role votes are merged across files so a cell like `HIGH RISK` absent from the blank template but present in a sample populates `risk_banner_bg` correctly.

### 3.4 Run directory layout

Each parsed artefact is written as `<original basename>.md` (extension replaced; spaces preserved). With Lumina Grand's actual files:

```
data/lumina_grand/Output/v0.1/
  parsed/
    APM/Lumina Grand_2. APM (8 Mar) (V3).md
    AWP/Lumina Grand_5. AWP (8 Mar) (V3).md
    Guidelines/Formatting Guidelines for report writing and proofreading for issue log issuance (v1.1).md
    Process SOP/CDL PDPA Manual - Final v1.md
    Process SOP/PDPA CDL Personal Data Policy Aug 2018_FINAL.md
    Process Understanding/PD_Roles_AccessRights_22Mar2024.md
    Process Understanding/Process Understanding - Lumina Grand PDPA.md
    Samples/1. Issue Log Template_version 11 Oct 2023.md   # FY2024 PDF NOT persisted
  constraints.json
  draft.json
  validation.json
  style_spec.json
  run.log
  Lumina Grand_Issue Log v0.1.docx
```

### 3.5 Held-out files

**`context.py` must exclude the approved FY2024 Lumina Grand PDF from both `<SAMPLES>` and disk persistence.** This file is the quality-gate ground truth — contaminating the prompt invalidates the evaluation. The empty `Issue Log Template v11 Oct 2023.docx` remains the sole `<SAMPLES>` content.

Hold-out list lives as a module-level constant in `context.py`:
```python
HELD_OUT_FILENAMES = {"FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf"}  # case-sensitive exact basename match
```

The held-out file is excluded from both `<SAMPLES>` context assembly and `parsed/` persistence.

---

## 4. Data contracts

### 4.1 `sample_issues.json` (input — hand-seeded)

Array of auditor-observed issues. Seeded by the engineer from the approved FY2024 report's findings (simulating auditor input).

```json
[
  {
    "title_hint": "PDPA training coverage",
    "observed_gap": "Not all employees handling personal data completed annual PDPA refresher.",
    "evidence_summary": "Training records (HR-LMS export) show 87% completion vs. 100% required by CDL PDPA Manual §4.2.",
    "evidence_refs": ["HR-LMS export 2024-Q3", "CDL PDPA Manual §4.2"],
    "sop_refs": ["CDL PDPA Manual §4.2"],
    "risk_category": "Compliance"
  }
]
```

| Field | Required | Purpose |
|---|---|---|
| `title_hint` | ✓ | Seed for the issue title; LLM may rephrase per `<GUIDELINES>` |
| `observed_gap` | ✓ | Auditor's description of the deviation |
| `evidence_summary` | ✓ | Free-text evidence summary |
| `evidence_refs` | ✓ | Array of citable references (at least 1) |
| `sop_refs` | ✓ | SOP sections the gap violates |
| `risk_category` | optional | Maps to APM risk focus |

Invariant: `len(draft) == len(sample_issues)` and order preserved.

### 4.2 `constraints.json` (Stage 3 output)

```json
{
  "audit_scope": "Personal Data Protection Act compliance across CDL Zenith entities for FY2024.",
  "audited_entities": ["CDL Zenith Pte Ltd", "Lumina Grand project office", "HR team"],
  "entity_legal_name": "CDL Zenith Pte Ltd",
  "project_name": "Lumina Grand",
  "fiscal_year": "FY2024",
  "key_risks": [
    "Unauthorized access to resident personal data",
    "Inadequate PDPA training coverage",
    "Data retention beyond policy period"
  ],
  "out_of_scope_items": ["IT infrastructure security", "Financial reporting controls"],
  "review_procedures": [
    {
      "scope": "Lumina Grand",
      "key_process": "Review of Operations Manual",
      "work_program": "Verify the Operations Manual is up-to-date and approved; confirm staff awareness."
    }
  ]
}
```

`entity_legal_name` / `project_name` / `fiscal_year` drive the DOCX header/footer strings. `review_procedures` enumerates every in-scope sub-process from the AWP's Summarised Work Program and is rendered verbatim as the "Internal Audit Review Procedures" appendix table (see §6.2).

### 4.3 `draft.json` (Stage 4 output)

```json
[
  {
    "id": "I-1",
    "category": "A. PERSONAL DATA PROTECTION ACT COMPLIANCE",
    "risk_level": "Medium",
    "title": "Strengthening annual PDPA training completion",
    "finding": "Review of HR-LMS records for FY2024 noted that 13% of personnel handling personal data did not complete the annual PDPA refresher required by CDL PDPA Manual §4.2.",
    "risk_impact": "- Incomplete training coverage increases the risk of PDPA breaches.\n- Regulatory scrutiny may flag this as a compliance gap.",
    "financial_impact": "Not applicable.",
    "recommendation": "- HR and the PDPA Compliance Officer should institute a quarterly tracking cadence.\n- Escalate outstanding completions to line managers by end of Q1 FY2025.",
    "evidence_refs": ["CDL PDPA Manual §4.2", "Process Understanding - Lumina Grand PDPA / §3"],
    "exceptions": {
      "title": "Table A1-1: Departments with sub-100% PDPA training completion",
      "headers": ["S/N", "Department", "Completion %", "Outstanding Headcount"],
      "column_aligns": ["center", "left", "right", "center"],
      "rows": [["1.", "Sales & Marketing", "82%", "9"]]
    },
    "root_cause": "Training tracking is annual-only; mid-year leavers/joiners are not reconciled.",
    "theme": "Process, Control Activities, Compliance",
    "action_plan": "",
    "responsibility": "",
    "target_date": "",
    "management_comments": ""
  }
]
```

Notes on the schema:
- `category` groups issues by sub-process under a banner row in the DOCX (e.g. "A. …", "B. …").
- `risk_level` drives both the summary-index H/M/L marker column and the per-issue risk banner color (see §4.5 style spec).
- `risk_impact` and `recommendation` are rendered as bulleted lists in the DOCX.
- `exceptions` is optional; omit the key entirely when no specific instances exist. When present, `column_aligns` length MUST equal `headers` length and each value is `"left"` / `"center"` / `"right"` per Guidelines §11 (names/descriptions left, dates/numbers/S-N centered, monetary right).
- Clustering rule: `len(draft) ≤ len(sample_issues)` — issues MAY be merged (e.g. a process gap + its exception rows), but NEVER split. Order is preserved.
- `action_plan` / `responsibility` / `target_date` / `management_comments` default to empty strings when `sample_issues.json` does not supply them; the drafter must not fabricate management responses.

### 4.4 `validation.json` (Stages 5 + 6 merged)

```json
{
  "context_truncated": false,
  "rule_based": {
    "passed": true,
    "warnings": []
  },
  "llm_critique": {
    "issues": [
      {
        "issue_id": "I-1",
        "flags": [
          {
            "type": "WEAK_EVIDENCE",
            "severity": "low",
            "excerpt": "13% of personnel",
            "reason": "Exact denominator not cited; source export total headcount unclear."
          }
        ]
      }
    ],
    "summary": "Draft stays within scope. One weak-evidence flag on I-1; otherwise clean."
  }
}
```

Flag types: `SCOPE_BREACH | UNSUPPORTED_ASSERTION | TONE_VIOLATION | WEAK_EVIDENCE`.
Severity: `low | medium | high`.
Both the rule-based and LLM critique are informational; neither blocks DOCX generation.

### 4.5 `style_spec.json` (Stage 6 output)

```json
{
  "page": {
    "orientation": "landscape",
    "size": "A4",
    "margin_inches": {"left": 1.0, "right": 1.0, "top": 1.0, "bottom": 1.0},
    "header_distance_inches": 0.49,
    "footer_distance_inches": 0.49,
    "page_break_type": "section_next_page"
  },
  "fonts": {
    "body":      {"family": "Arial", "size_pt": 10},
    "exception": {"family": "Arial", "size_pt": 9}
  },
  "paragraph_spacing": {
    "body":      {"before_pt": 6, "after_pt": 6, "line_at_least_pt": 13},
    "exception": {"before_pt": 3, "after_pt": 3, "line_at_least_pt": 13}
  },
  "colors": {
    "summary_header_bg":     "FADFA0",
    "issue_table_header_bg": "FFE599",
    "category_banner_bg":    "D9D9D9",
    "risk_banner_bg":        "FFF2CC",
    "risk_level_marker": {"High": "C00000", "Medium": "FFC000", "Low": "00B050"}
  },
  "notes": "Short prose on where template/Guidelines agreed vs. disagreed."
}
```

Precedence inside `normalise_style_spec`: `DEFAULT_STYLE_SPEC` → LLM output merged on top → `template_analysis.roled_colors` and `margin_inches` applied as ground-truth overrides → hard clamps (`orientation="landscape"`, `size="A4"`, `page_break_type ∈ {"section_next_page","page"}`, header/footer distances positive). If the LLM step fails entirely, the default merged with template overrides is emitted and the failure is logged as a non-fatal WARN.

`page_break_type="section_next_page"` is mandated by Guidelines §9 (plain page breaks forbidden). Header/footer distances default to 0.49 in. per §18/§19.

---

## 5. Prompt strategy

### 5.1 Step 1 — Constraint extraction (`prompts/constraints.py`)

**System:** "You are an Internal Audit scope extractor. You read an Approved Work Program (AWP) and Approved Planning Memo (APM) for a single audit engagement and emit a structured scope envelope. You do not invent scope items or entities not present in the inputs."

**User message:**
```
<AWP>{awp_text}</AWP>
<APM>{apm_text}</APM>

Return a single JSON object matching this schema:
{
  "audit_scope": "<one-paragraph description>",
  "audited_entities": ["<entity>", ...],
  "key_risks": ["<risk statement>", ...],
  "out_of_scope_items": ["<item>", ...]
}
Rules:
- Only include entities named in the AWP or APM.
- key_risks must reflect the APM's stated risk focus, not generic audit risks.
- If out-of-scope items are not explicitly stated, return an empty array.
Respond with JSON only, inside a ```json fenced block.
```

**Call parameters:** temperature `0.2`, max_tokens `2048`.

### 5.2 Step 2 — Issue drafting (`prompts/drafting.py`)

**System:** "You are an Internal Audit issue-log drafter. You draft professional audit issues from auditor-provided observations, staying strictly within the audit scope and citing only evidence from supplied artefacts. You write in the constructive, positive-title house style shown in `<SAMPLES>`. You are a drafting assistant — you do not invent findings, recommend beyond evidence, or expand scope."

**User message:** Produces a JSON array conforming to the rich schema in §4.3 (`id`, `category`, `risk_level`, `title`, `finding`, `risk_impact`, `financial_impact`, `recommendation`, `evidence_refs`, optional `exceptions` with `column_aligns`, `root_cause`, `theme`, and the four management-response fields).

Rules embedded in the user template:
- **Clustering**: if multiple `<AUDITOR_INPUT>` items share the same root cause OR one is the exception-detail of another, MERGE them into a single issue (narrative in `finding`, specific instances in `exceptions`). Otherwise preserve input order. May emit fewer issues than inputs, never more.
- **Titles**: positive-framed per Guidelines §13. Forbidden patterns: "Failure to X", "Non-compliance of X", "X was not done".
- **Scope**: every issue inside `audit_scope` and `audited_entities` from `<SCOPE>`.
- **Evidence**: `evidence_refs` must cite `<SOP>` or `<PROCESS_UNDERSTANDING>` with document name + section/sheet/page. No fabricated quotes.
- **Financial impact**: "Not applicable." unless an SGD amount is directly stated in `<AUDITOR_INPUT>` or `<PROCESS_UNDERSTANDING>`.
- **Exceptions**: omit the key entirely if no specific instances. When present, `column_aligns` length MUST equal `headers` length per Guidelines §11.
- **Management-response fields**: empty strings unless provided (no invented commitments).
- Tone, structure, and category-banner style must match `<SAMPLES>`.

Respond with JSON only inside a ```json fenced block.

**Call parameters:** temperature `0.3`, max_tokens `6144`.

**Key design calls:**
- `<SAMPLES>` contains *only* the past-audit issue-log reference DOCX; FY2024 PDF is held out.
- `<AWP>`/`<APM>` are not re-sent — distilled form lives in `<SCOPE>`.
- Model assigns `id` field (`I-1`, `I-2`, …) so Step 3 can address issues by ID.

### 5.3 Step 3 — Self-critique (`prompts/critique.py`)

**System:** "You are an Internal Audit reviewer. You inspect a draft issue log against the audit scope, writing guidelines, and source evidence. You flag issues — you do not rewrite them. Be specific: quote the exact problematic excerpt."

**User message:**
```
<SCOPE>{constraints.json}</SCOPE>
<GUIDELINES>{guidelines_text}</GUIDELINES>
<SOP>{sop_text}</SOP>
<PROCESS_UNDERSTANDING>{pu_text}</PROCESS_UNDERSTANDING>
<DRAFT>{draft.json}</DRAFT>

Review each issue in <DRAFT>. Return JSON:
{
  "issues": [
    {"issue_id": "I-1",
     "flags": [
       {"type": "SCOPE_BREACH" | "UNSUPPORTED_ASSERTION"
              | "TONE_VIOLATION"  | "WEAK_EVIDENCE",
        "severity": "low" | "medium" | "high",
        "excerpt": "<verbatim text from the draft>",
        "reason": "<one sentence>"}
     ]}
  ],
  "summary": "<2-3 sentence overall assessment>"
}
Flag types:
- SCOPE_BREACH: content references entities or activities outside <SCOPE>.
- UNSUPPORTED_ASSERTION: claim cannot be traced to <SOP> or <PROCESS_UNDERSTANDING>.
- TONE_VIOLATION: title or phrasing conflicts with <GUIDELINES>.
- WEAK_EVIDENCE: evidence_refs exist but do not substantiate the finding.
If an issue is clean, return "flags": [].
Respond with JSON only, inside a ```json fenced block.
```

**Call parameters:** temperature `0.1`, max_tokens `2048`.

### 5.4 Step 4 — Style spec production (`prompts/styling.py`)

**System:** "You produce a JSON style specification for a DOCX renderer. Reconcile the prose rules in `<GUIDELINES>` with the concrete palette observed in `<TEMPLATE_ANALYSIS>`. Where they conflict, prefer the template's actual values (the template is ground truth). Hex colors must be 6 uppercase characters with no `#`."

**User message:** includes `<GUIDELINES>`, `<TEMPLATE_ANALYSIS>` (output of `template_inspector.inspect_templates`, merged over `template.docx` + `Samples/*.docx`), and `<DRAFT>` (so the LLM knows which elements are in play). Returns the JSON object shown in §4.5.

Rules embedded in the user template:
- `orientation` MUST be `"landscape"`, `size` MUST be `"A4"` (house defaults).
- `page_break_type` MUST be `"section_next_page"` per Guidelines §9.
- Fonts and spacing follow Guidelines §1 and §2.
- `header_distance_inches` / `footer_distance_inches` follow §18/§19 (typically 0.49).
- Colors must be filled from `<TEMPLATE_ANALYSIS>.fill_colors` using role cues in neighbouring cells ("S/N" / "Findings" → issue table header; "A." / "B." → category banner; "HIGH RISK" / "MEDIUM RISK" / "LOW RISK" → risk banner; "X" cells under H/M/L headers → per-risk markers; cells under "Issues" / "Audit Risk Level" → summary header).
- When a level is missing from the template, infer from Guidelines §24 (High = red, Medium = amber, Low = green).

**Call parameters:** temperature `0.0`, max_tokens `1024`.

**Failure tolerance:** the main pipeline wraps this call in `try`/`except`; any exception (including JSON-parse failure after the single retry) is logged as a non-fatal WARN in `run.log` and `normalise_style_spec(None, template_analysis)` is used instead.

### 5.5 Prompt cross-cutting conventions

- Every LLM response logs `input_tokens` / `output_tokens` from `response.usage` into `run.log`.
- JSON-only response; fenced `json` block; `llm.py` extracts via first `json` fence or first balanced `{...}`.
- Retry matrix in §7.1.

---

## 6. Validation, rendering, versioning

### 6.1 Rule-based validation (`src/validate.py`)

**Check A — `check_evidence_refs(draft)`:** every issue has ≥1 non-empty `evidence_refs` entry.

**Check B — `check_scope(draft, constraints)`:**
- Flag any issue whose combined text contains a term from `constraints.out_of_scope_items` (case-insensitive substring).
- Soft-flag any issue that does not mention at least one `audited_entity` (possible scope drift).

Both checks append warning strings to `validation.json.rule_based.warnings`. `passed == (len(warnings) == 0)`. The pipeline continues regardless.

### 6.2 DOCX rendering (`src/render.py`)

**Layout contract (template-palette faithful, landscape A4):**
- **Title row** — project / legal entity / fiscal year banner, row-heights matching `Samples/` values (680/43/567 twips).
- **Summary index table (T1)** — two columns (`Issues` / `Audit Risk Level`) with per-row H/M/L markers. Category banners repeat per sub-process. Backgrounds from `style_spec.colors.summary_header_bg` and `issue_table_header_bg`.
- **Risk banner strip (T2)** — single-row per risk level cell (`HIGH RISK` / `MEDIUM RISK` / `LOW RISK`) filled with `risk_banner_bg`.
- **Per-issue table (T3…)** — one 2-column grid per issue with section rows: Finding, Risk / Impact, Financial Impact, Recommendation, (optional) Exceptions sub-table, Root Cause, Theme, Action Plan, Responsibility, Target Date, Management Comments. Category banner inserted before each issue group.
- **Exception sub-tables** — font dropped to `style_spec.fonts.exception.size_pt`, per-column alignment from `draft.exceptions.column_aligns` (Guidelines §11).
- **Review Procedures appendix (T7)** — rendered from `constraints.review_procedures`: three columns (`Scope / Key Process / Summarised Work Program`), on a fresh section (`page_break_type`).
- Section breaks between major blocks per Guidelines §9 (`doc.add_section(WD_SECTION.NEW_PAGE)`), NOT plain page breaks.
- Header/footer distances from `style_spec.page.{header,footer}_distance_inches`; margins from `style_spec.page.margin_inches`.

Critique flags are **not** rendered inline in the DOCX. Auditor reads `validation.json` alongside.

### 6.3 Versioning (`src/versioning.py`)

```python
import re
from pathlib import Path

VERSION_RE = re.compile(r"^v0\.(\d+)$")

def next_version(project_path: Path) -> tuple[str, Path]:
    output_root = project_path / "Output"
    output_root.mkdir(exist_ok=True)
    existing = [
        int(m.group(1))
        for d in output_root.iterdir()
        if d.is_dir() and (m := VERSION_RE.match(d.name))
    ]
    n = (max(existing) + 1) if existing else 1
    version = f"v0.{n}"
    run_dir = output_root / version
    run_dir.mkdir()
    return version, run_dir
```

**Never overwrite an existing `v0.N` directory.** `main.py` calls `next_version` up-front and all stages write into that directory.

**Legacy files:** pre-existing `.docx` files at the flat `Output/` root are ignored — the scanner only looks at directories matching `v0.\d+`.

---

## 7. Error handling & runtime behaviour

### 7.1 Error tiers

| Tier | Examples | Policy |
|---|---|---|
| **Setup (fatal, exit 1)** | Missing `ANTHROPIC_API_KEY`, project folder absent, `sample_issues.json` missing/malformed, no files in AWP/APM | `print(..., file=sys.stderr); sys.exit(1)` with a specific message |
| **Parsing (warn, continue)** | Corrupt DOCX, PDF page extraction fails, unknown folder | Log warning to `run.log` + console; skip file; stage continues |
| **LLM (retry, then fail)** | 429, 5xx, timeout, malformed JSON | Bounded retry in `llm.py`; after exhaustion, persist partial state and exit 1 |

### 7.2 LLM retry

- 3 attempts with exponential backoff (`1s, 2s, 4s`) on `RateLimitError` and 5xx `APIStatusError`.
- Non-429 4xx errors re-raise immediately (our bug — surface it).
- JSON-parse failure triggers exactly one retry with a reminder message ("Your previous reply was not valid JSON. Respond with JSON only, inside a ```json fenced block.").
- Two consecutive JSON-parse failures → stage raises; `main.py` persists whatever stage outputs succeeded and exits 1. Run directory is preserved so the auditor can inspect how far the pipeline got.

### 7.3 `run.log`

Plain text, one line per event, timestamp + stage + message, written incrementally so a crash leaves a partial log usable for diagnosis.

```
2026-04-18 19:22:03 [parse]       Read 3 DOCX, 2 PDF, 1 XLSX from data/lumina_grand
2026-04-18 19:22:04 [parse]       WARN: Process SOP/foo.pdf — extractor returned empty
2026-04-18 19:22:05 [context]     Built context: 187,432 chars; FY2024.pdf excluded
2026-04-18 19:22:05 [step1]       Calling claude-sonnet-4-5 (temp=0.2, max_tokens=2048)
2026-04-18 19:22:11 [step1]       OK. in=14,281 out=412 tokens
```

### 7.4 Context budget & truncation

Sonnet 4.5 window is 200k tokens. Lumina Grand corpus (~7 MB binary) should extract well under budget; we defend against regressions with a character-count guard in `context.py`.

```python
CHAR_BUDGET = 600_000   # ~150k tokens at ~4 chars/token; leaves headroom for prompt scaffolding
TRUNCATION_ORDER = ["SOP", "PROCESS_UNDERSTANDING", "GUIDELINES",
                    "SAMPLES", "APM", "AWP"]
```

If total exceeds budget, tail-truncate blobs in `TRUNCATION_ORDER` until under. Each truncation writes a warning to `run.log` and sets `validation.json.context_truncated = true` so the auditor can discount edge findings.

---

## 8. CLI

Single entry point. Always re-parses (no cache).

```bash
python main.py --project data/lumina_grand --issues sample_issues.json
```

Arguments:
- `--project <path>` — path to the project root containing the 6 folders. Required.
- `--issues <path>` — path to `sample_issues.json`. Required.

Per-stage progress banners print to stdout (ASCII only — Windows cp1252 cannot encode `…` / `→`):
```
[1/8] Parsing ...
[2/8] Building context ...
[3/8] Extracting constraints ...
[4/8] Drafting issues ...
[5/8] Self-critiquing ...
[6/8] Producing style spec ...
[7/8] Rule-based validation ...
[8/8] Rendering DOCX ...
-> data/lumina_grand/Output/v0.1/Lumina Grand_Issue Log v0.1.docx
```

---

## 9. Testing strategy

**No unit test suite in the POC.** Replace with:

1. **`test_connection.py`** — API smoke test; run before each real pipeline run.
2. **Walking-skeleton runs** — end-to-end `main.py` at every day's exit criterion.
3. **Persistent intermediate JSON** — stage-by-stage eyeballing without re-running the LLM.
4. **Manual golden comparison** — side-by-side diff of generated DOCX vs. the held-out FY2024 report.

Tests earn their way in via concrete bugs:
- A parser misbehaves on more than one document → extract a fixture, write a targeted test.
- `extract_json` fails on a real LLM response → capture verbatim, write a regression test.

---

## 10. Success criteria

The POC is successful when all of the following hold on a clean run:

1. `python main.py --project data/lumina_grand --issues sample_issues.json` completes with exit 0.
2. `data/lumina_grand/Output/v0.1/Lumina Grand_Issue Log v0.1.docx` exists and opens in Word.
3. The DOCX contains one 4-row table per item in `sample_issues.json`, in the same order, with non-empty Finding / Impact / Recommendation / Evidence cells.
4. A second run produces `v0.2/` without touching `v0.1/`.
5. `constraints.json` captures the Lumina Grand PDPA scope and entities correctly (manual eyeball).
6. `draft.json` passes both rule-based checks, or the warnings surfaced are genuine (not false positives).
7. `validation.json.llm_critique` has at most one medium-severity flag per issue on average; no high-severity `SCOPE_BREACH` flags.
8. Manual comparison: at least one generated issue maps to a finding in the held-out FY2024 PDF, even if phrased differently; no fabricated findings.

---

## 11. Hard rules (preserve under schedule pressure)

- **The 4-step LLM chain.** Steps 1-3 (constraints / drafting / critique) are core correctness signals and must not be dropped without a reset of the success criteria. Step 4 (styling) is tolerant — its failure falls back to `DEFAULT_STYLE_SPEC` + template overrides, so the DOCX still renders.
- **FY2024 hold-out.** Contaminating the prompt with the ground-truth report invalidates the evaluation story.
- **Versioned output directories.** Overwriting a prior run destroys audit trail.

## 12. Acceptable fallbacks if Day 5 gets eaten

- Drop `check_scope` (LLM critique covers scope drift).
- Drop context-budget truncation code (leave the measurement + warning only).
- Drop nested `parsed/*.md` persistence (keep JSON handoffs only).

---

## 13. Open items (none blocking)

- Configurable hold-out list via CLI flag — current hold-out is hard-coded; move to config if a second held-out artefact is needed.
- Token-count verification: measure actual tokens on first real run; revisit `CHAR_BUDGET` if estimate is off.
- Inspector role-vote weighting: currently every DOCX (blank template + samples) votes equally; consider weighting the blank template higher for layout-critical roles (margins, fonts) where applicable.
