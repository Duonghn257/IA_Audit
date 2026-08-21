"""Step 2 — draft issues from auditor input + artefacts."""
from __future__ import annotations

import json
from typing import Any

import anthropic

from app.ai.client import LLMResult, call_json
from app.rag.context import wrap

SYSTEM = (
    "You are an Internal Audit issue-log drafter. You draft professional "
    "audit issues from auditor-provided observations, staying strictly "
    "within the audit scope and citing only evidence from supplied "
    "artefacts. You write in the constructive, positive-title house style "
    "shown in <SAMPLES>. You are a drafting assistant -- you do not invent "
    "findings, recommend beyond evidence, or expand scope."
)

USER_TEMPLATE = """{scope_block}

{guidelines_block}

{samples_block}

{sop_block}

{pu_block}

{auditor_input_block}

Produce a JSON array of issues. Each issue must follow this schema:

[{{
  "id": "I-1",
  "category": "<sub-process grouping, e.g. 'A. PERSONAL DATA PROTECTION ACT COMPLIANCE'>",
  "risk_level": "High" | "Medium" | "Low",
  "title": "<positive-tone header per <GUIDELINES> section 13>",
  "finding": "<narrative describing the gap, grouped by sub-issue if needed>",
  "risk_impact": "<bulleted list of risks>",
  "financial_impact": "<amount in SGD, or 'Not applicable.'>",
  "recommendation": "<bulleted actions, constructive tone>",
  "evidence_refs": ["<verbatim snippet or file.sheet/section from <SOP>/<PROCESS_UNDERSTANDING>>", ...],
  "exceptions": {{
    "title": "<e.g. 'Table A1-1: <descriptive title>'>",
    "headers": ["S/N", "<col 1>", "<col 2>", ...],
    "column_aligns": ["center", "left", "center", "right", ...],
    "rows": [["1.", "<val>", "<val>", ...], ...]
  }},
  "root_cause": "<one sentence, per <GUIDELINES> section 16>",
  "theme": "<People|Process|System>, <Control Activities|...>, <Operational|Strategic|Compliance>",
  "action_plan": "<management action plan, or empty string if not provided>",
  "responsibility": "<Name, Designation, or empty>",
  "target_date": "<date spelt in full, 15th of month, or 'Implemented', or empty>",
  "management_comments": "<optional, empty string if none>"
}}]

Clustering rule:
- If multiple items in <AUDITOR_INPUT> share the same root cause OR one is
  the exception detail of another (e.g. a process-gap observation and its
  specific exception rows), MERGE them into a single issue. Put the
  narrative of the process gap in "finding" and the specific instances in
  the "exceptions" table.
- Otherwise preserve each input as its own issue, in order.
- You MAY emit fewer issues than inputs (when merging) but NEVER more.

Formatting rules (from <GUIDELINES>):
- Titles must be positive-framed per section 13. Acceptable patterns:
  "X should be enhanced/strengthened/complied with/adhered to",
  "X could be strengthened", "Enhance X". Forbidden patterns:
  "Failure to X", "Non-compliance of X", "X was not done".
- evidence_refs must cite <SOP> or <PROCESS_UNDERSTANDING>. Include the
  document name and the section/sheet/page where the evidence lives. Do
  not fabricate quotes; prefer verbatim short excerpts or exact section
  references.
- Every issue must stay inside audit_scope and audited_entities in <SCOPE>.
- "financial_impact" is "Not applicable." unless a dollar amount is
  directly stated in <AUDITOR_INPUT> or <PROCESS_UNDERSTANDING>.
- If the input does not specify action_plan / responsibility / target_date
  / management_comments, return empty strings for those fields (do not
  invent management responses).
- If the finding has no specific exception instances, omit the "exceptions"
  key entirely (do not emit an empty table).
- For each exception table, emit "column_aligns" with one value per column
  following <GUIDELINES> section 11:
    * "left"   -> Names, Descriptions, Bullet points (text content)
    * "center" -> Dates, non-monetary Numbers, S/N
    * "right"  -> Monetary amounts (e.g. SGD values)
  The list length MUST equal len(headers).
- Tone, structure, and category header style must match <SAMPLES>.

Respond with JSON only, inside a ```json fenced block."""


def draft_issues(
    client: anthropic.Anthropic,
    model: str,
    *,
    constraints: dict[str, Any],
    guidelines: str,
    samples: str,
    sop: str,
    process_understanding: str,
    auditor_input: list[dict[str, Any]],
) -> LLMResult:
    user = USER_TEMPLATE.format(
        scope_block=wrap("SCOPE", json.dumps(constraints, indent=2)),
        guidelines_block=wrap("GUIDELINES", guidelines),
        samples_block=wrap("SAMPLES", samples),
        sop_block=wrap("SOP", sop),
        pu_block=wrap("PROCESS_UNDERSTANDING", process_understanding),
        auditor_input_block=wrap(
            "AUDITOR_INPUT", json.dumps(auditor_input, indent=2)
        ),
    )
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=6144, temperature=0.3,
    )
