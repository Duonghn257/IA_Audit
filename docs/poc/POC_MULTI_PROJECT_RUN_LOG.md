# Multi-project POC run log

**Date:** 2026-05-04  
**Command pattern:** `python main.py --project "<data/<project>/>" --issues "<project>/sample_issues.json"`  
**Scope:** All folders under `data/` **except** `lumina_grand` (11 audit projects).

## Executive summary

| Outcome | Count |
|--------|------:|
| Pipeline completed (exit code 0) | 11 |
| Pipeline crashed (non-zero exit / parse exception) | 0 |

All runs produced `Output/v0.1/` artefacts (DOCX, `parsed/`, `constraints.json`, `draft.json`, `validation.json`, `style_spec.json`, `run.log`).

The POC treats **rule-based validation** and **LLM self-critique** as informational: a `rule_based.passed: false` result does **not** stop the run or delete the DOCX. The items below are **quality / guardrail flags**, not hard runtime errors.

---

## Context assembly warning (not a project “failure”)

### IA2025-01 St Katharine Docks (Completed)

- **Symptom:** `run.log` records: `<SOP> tail-truncated by 722,800 chars` after assembling context to the 600,000-character budget (`src/context.py` `CHAR_BUDGET`).
- **Reason:** The project has a very large amount of parseable text at the top level of `Process SOP/` (and other folders). To stay within the budget, the SOP blob is tail-truncated, so later SOP pages/files may never reach the LLM.
- **Impact:** Constraints and drafts may miss procedures that would have appeared in the truncated tail; scope and citations can be incomplete relative to the full file set.
- **Rule-based validation:** `passed: true` for this run; the truncation is still a material limitation for review.

---

## Rule-based validation: `passed: false`

The validator flags issues such as missing `audited_entity` in draft text (possible scope drift) and, in one case, an out-of-scope keyword. Details below are taken from each project’s `Output/v0.1/validation.json`.

### IA2024-01 CDL Properties Ltd (Republic Plaza II) (Completed)

| Check | Detail |
|-------|--------|
| **rule_based** | `passed: false` — 1 warning |
| **Warnings** | `I-1: no audited_entity mentioned (possible scope drift)` |
| **LLM critique (summary)** | Draft issues cite policy in ways that do not match current documents (e.g. outdated Annex C / Vendor Management Policy), conflate policy versions without effective dates, or assert deviations (e.g. tender deposit payee) without establishing the contractual “tender calling company”. Flags: `UNSUPPORTED_ASSERTION` (medium/low) on both I-1 and I-2. |

### IA2024-03 Aquarius Properties Pte Ltd (Amber Park) (Completed)

| Check | Detail |
|-------|--------|
| **rule_based** | `passed: false` — 2 warnings |
| **Warnings** | `I-1` and `I-2`: `no audited_entity mentioned (possible scope drift)` |
| **LLM critique (summary)** | Findings read as generic “audit seeks to verify” / “need to verify” without concrete testing exceptions from `<PROCESS_UNDERSTANDING>`. I-1’s narrative conflicts with cited control text (documentation digitised and saved). Flags: `UNSUPPORTED_ASSERTION` (high/medium), `WEAK_EVIDENCE`. |

### IA2024-05 Hong Leong Technology Park Shenzhen (HLTPS) (Completed)

| Check | Detail |
|-------|--------|
| **rule_based** | `passed: false` — 1 warning |
| **Warnings** | `I-1: no audited_entity mentioned (possible scope drift)` |
| **LLM critique (summary)** | Process-understanding observations are framed as deficiencies though the source does not clearly label them as gaps; undefined `[AP]` tag in PU; generic evidence refs for the annual work plan. Flags: `UNSUPPORTED_ASSERTION` (medium/low), `WEAK_EVIDENCE`. |

### IA2025-07 Appointment of Contractors and Consultants (via SAP Ariba)

| Check | Detail |
|-------|--------|
| **rule_based** | `passed: false` — 2 warnings |
| **Warnings** | `I-1: no audited_entity mentioned (possible scope drift)`; `I-2: mentions out-of-scope item 'segregation of duties'` |
| **LLM critique (summary)** | I-1: wording on management action vs audit-triggered enhancement. I-2: strong SoD narrative not fully supported (e.g. “disable notifications”); conflation of user-ID approval vs project assignment; date `21 May 2025` vs fieldwork timeline may be inconsistent. Flags: `UNSUPPORTED_ASSERTION` (high/medium), `WEAK_EVIDENCE`. |

### IT2025-04 SAP Ariba Access Controls Review (Completed)

| Check | Detail |
|-------|--------|
| **rule_based** | `passed: false` — 2 warnings |
| **Warnings** | `I-1` and `I-2`: `no audited_entity mentioned (possible scope drift)` |
| **LLM critique (summary)** | Table label / PU labelling mismatch (“custodians” vs “consultants”); several factual claims inferred from PU rather than directly quoted (e.g. superadmin non-use, tracker fields); “excessive permissions” not fully detailed in evidence. Flags: `UNSUPPORTED_ASSERTION` (high/medium/low), `WEAK_EVIDENCE`. |

---

## Rule-based validation: `passed: true`

The following batch runs reported `rule_based.passed: true` and zero rule-based warnings in `validation.json`:

- IA 2025-02M Mini Audit – CDL E-Voucher Transactions in CityNexus  
- IA 2025-03M Mini Audit – Palais – Maintenance of Property and Equipment  
- IA 2025-05M Mini Audit – CDL AP – Management of Bank Account Changes  
- IA2024-02 CDL Zenith Pte Ltd (Lumina Grand) (Completed)  
- IA2024-02 CDL Zenith Pte Ltd (Lumina Grand) (Updated)  

*(Lumina Grand Updated merged two seed inputs into one drafted issue in the logged run — still completed successfully.)*

---

## Where to look per project

For any project listed above:

- `data/<project>/Output/v0.1/validation.json` — full `rule_based` and `llm_critique` payloads  
- `data/<project>/Output/v0.1/run.log` — parse counts, context truncation warnings, token summaries  

---

## Document control

| Item | Value |
|------|--------|
| Purpose | Record multi-project POC outcomes and validation/truncation reasons |
| Audience | Developers / IA pilot users |
| Generated from | Batch run 2026-05-04; validator behaviour in `src/validate.py` |
