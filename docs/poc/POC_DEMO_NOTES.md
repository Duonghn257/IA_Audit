# POC Demo Notes — Lumina Grand

**Run:** `data/lumina_grand/Output/v0.3/Lumina Grand_Issue Log v0.3.docx`
**Date:** 2026-04-18
**Auditor input:** 2 seeded issues from `backend/sample_issues.json`
**Ground truth:** `data/lumina_grand/Samples/FY2024 Audit of CDL Zenith Pte Ltd (Lumina Grand).pdf` (held out from `<SAMPLES>` context)

## What the POC does well

- **Positive-framed titles per Guidelines §2.1.** Both draft titles use "should be" phrasing — "Annual Salesforce access rights review should be enhanced to include profile-level permissions" and "Salesforce user profile permissions should be aligned with employee job responsibilities" — matching the approved FY2024 finding's style ("Annual review of access rights for Salesforce Sales Cloud should be strengthened").
- **Evidence citations trace to real corpus documents.** All 7 `evidence_refs` across both issues point to actual files in the project folder — `CDL PDPA Manual – Chapter 4`, `PD_Roles_AccessRights_22Mar2024.xlsx` (sheets `IA-Edit`, `CDL Sales User`, `CDL Marketing User`), `Process Understanding - Lumina Grand PDPA.docx` section E.1.2. No fabricated sources.
- **Constraint extraction captured the engagement envelope accurately.** `constraints.json` enumerated both audited entities (`CDL Zenith Pte Ltd`, `Lumina Grand`), 13 key risks lifted from the AWP/APM (including SM-2, SM-6, SM-7, R7, R8 risk codes), and the single out-of-scope item (Sales Channel Management) — providing the scope guardrail the drafting and critique steps use.
- **Self-critique surfaced substantive issues, not cosmetic ones.** 7 critique flags total — the 2 high-severity `UNSUPPORTED_ASSERTION` flags caught real problems: the draft's claim "confirmed through walkthrough discussions" isn't backed by Process Understanding (which only documents an email-based review), and the assertion about "CDL PDPA Manual" explicitly mandating annual profile-level reviews overstates what Chapter 4 actually says.
- **Staff names, titles, and per-object permissions propagated verbatim** from `sample_issues.json` into the draft (Chua Wan Khi AVP, Rachel Ong Senior Manager, Samantha Tan Senior Manager; Leads/Accounts/Contacts Read/Create/Edit/Delete breakdowns) — matching the exception rows in FY2024 Table A1-1.

## Gaps vs. the approved FY2024 report

- **Structural split: 1 FY2024 finding → 2 POC issues.** FY2024 reports a single Low-risk finding (A1) combining the process gap *and* the three exception rows, with Table A1-1 as a sub-table of the same finding. The POC produced I-1 (process gap) and I-2 (exceptions) as separate issues, with manual cross-references ("Refer to Observation A2" / "refer to Observation A1") that wouldn't exist in the approved form. This is a direct consequence of honoring `N-in = N-out`: `sample_issues.json` had two hand-seeded entries.
- **Verbosity: draft is ~3× longer per finding.** FY2024's A1 narrative is ~120 words of tight prose plus a compact exception table. The POC's I-2 alone runs ~380 words with bulleted per-employee sub-breakdowns before reaching the same exception table. FY2024's style is declarative; the POC's is explanatory.
- **Missing schema fields carried by FY2024.** The approved report has `Action Plan`, `Root Cause`, `Theme`, `Responsibility` (named officers), and `Target Date` (`15 August 2024`) columns alongside Finding/Impact/Recommendation. The POC `draft.json` schema only emits `title`, `finding`, `impact`, `recommendation`, `evidence_refs`, so these fields are absent from the DOCX.
- **Exception table not emitted as a true table.** FY2024's Table A1-1 is a formatted DOCX table (S/N, Employee, Assigned Profile, Object, Permissions). The POC inlines the same data as prose bullets inside `finding` — readable, but not the approved format.
- **`Report Rating` page, `Background Information`, `Scope of Review`, `Summary of Audit Findings` cover-page infographics are absent.** The POC renders only the issue log (one 4-row table per issue); FY2024 is a full 16-page report with executive summary, scope, methodology, definitions, distribution list, and appendix.

## Validation surface

- **Rule-based warnings:** 2 warnings, both of the form `"I-N: no audited_entity mentioned (possible scope drift)"`. Both are **false positives** — the issue text refers to "Salesforce", "S&M", "CDL PDPA Policy", and the three CDL employee names, but doesn't contain the literal substrings `"CDL Zenith Pte Ltd"` or `"Lumina Grand"`. The rule is a naive `substring in text` check; an NER- or lemma-based check would clear these.
- **LLM critique flags:** 7 total — **2 high** (`UNSUPPORTED_ASSERTION` in I-1: "confirmed through walkthrough discussions" and "control deficiency under CDL's Protection Obligation as set out in the CDL PDPA Manual"), **5 medium** (3 × `UNSUPPORTED_ASSERTION` in I-2 about "Wan Khi and Rachel do not access the Leads module", "Create and Edit permissions are not required", "Samantha does not use the Accounts module"; 2 × `WEAK_EVIDENCE` about generic reference labels). No `SCOPE_BREACH` or `TONE_VIOLATION` flags — scope and tone are clean.
- `context_truncated`: `false`. Full corpus fit under the context budget.

## Which full-build modules would close each gap

| Gap | Full-build module |
|---|---|
| Structural split of one finding into two (`N-in=N-out` artefact) | **Harvester + Sorter agents** (spec §10) — cluster auditor inputs into findings before drafting, so one finding with multiple exceptions stays one finding. |
| Verbosity / explanatory style vs. FY2024's declarative tone | **Review Agent** (spec §10) — a style critic pass that compresses to sample-guide tone; also **M4 smart section selection** to prevent over-paraphrasing of supporting context. |
| Missing Action Plan / Root Cause / Theme / Responsibility / Target Date fields | **M6 DOCX Rendering — template fidelity** (WBS M6) — extend `draft.json` schema + render to match `Output/template.docx` column structure. |
| Exception table emitted as prose rather than a DOCX table | **M6 template fidelity** — render structured `exceptions[]` arrays as proper Word tables. |
| Rule-based scope check false positives | **M5 Guardrails — scope check** (WBS M5) — replace substring match with NER + entity linking so `"CDL Zenith"` / `"Lumina Grand"` / aliases all satisfy the rule. |
| High-severity `UNSUPPORTED_ASSERTION` flags (draft claims facts not in Process Understanding) | **M5 citation check** (WBS M5) — per-claim evidence linking during drafting, not only at critique time; prevents the claim from being written in the first place. |
| No cover page / background / scope / distribution-list sections | Out of scope for POC. Future **M6 template fidelity** + a separate "front matter" prompt drawing from APM/AWP. |

## Ready-to-demo command

```bash
python backend/main.py --project data/lumina_grand --issues backend/sample_issues.json
```

Produces a fresh `data/lumina_grand/Output/v0.N/` (auto-incrementing N) containing `constraints.json`, `draft.json`, `validation.json`, `run.log`, `parsed/`, and `Lumina Grand_Issue Log v0.N.docx`.
