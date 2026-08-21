"""Step 1 — constraint extraction from AWP + APM."""
from __future__ import annotations

from typing import Any

import anthropic

from app.ai.client import LLMResult, call_json

SYSTEM = (
    "You are an Internal Audit scope extractor. You read an Approved Work "
    "Program (AWP) and Approved Planning Memo (APM) for a single audit "
    "engagement and emit a structured scope envelope. You do not invent "
    "scope items or entities not present in the inputs."
)

USER_TEMPLATE = """<AWP>
{awp}
</AWP>

<APM>
{apm}
</APM>

Return a single JSON object matching this schema:
{{
  "audit_scope": "<one-paragraph description>",
  "audited_entities": ["<entity>", ...],
  "entity_legal_name": "<primary audited legal entity (e.g. 'CDL Zenith Pte Ltd')>",
  "project_name": "<primary project name if applicable (e.g. 'Lumina Grand'), else ''>",
  "fiscal_year": "<FY label as shown in AWP/APM (e.g. 'FY2024'), else ''>",
  "key_risks": ["<risk statement>", ...],
  "out_of_scope_items": ["<item>", ...],
  "review_procedures": [
    {{
      "scope": "<audit scope / project the procedure covers (e.g. 'Lumina Grand')>",
      "key_process": "<sub-process name (e.g. 'Review of Operations Manual')>",
      "work_program": "<summarised work program description, verbatim or concise paraphrase from AWP>"
    }}
  ]
}}

Rules:
- Only include entities named in the AWP or APM.
- entity_legal_name should be the first corporate entity in audited_entities (prefer one with 'Pte Ltd', 'Ltd', or similar suffix).
- fiscal_year must match exactly as written in the AWP/APM (verbatim, e.g. 'FY2024', 'FY2023/24').
- key_risks must reflect the APM's stated risk focus, not generic audit risks.
- If out-of-scope items are not explicitly stated, return an empty array.
- review_procedures must enumerate every in-scope sub-process from the AWP's Summarised Work Program, in document order. Exclude rows marked 'In Scope? = No'. Use the AWP's own wording for key_process and work_program; do not invent procedures. The 'scope' field should be the project/scope grouping the sub-process belongs under (typically the project name, repeated across rows).

Respond with JSON only, inside a ```json fenced block."""


def extract_constraints(
    client: anthropic.Anthropic,
    model: str,
    awp: str,
    apm: str,
) -> LLMResult:
    user = USER_TEMPLATE.format(awp=awp, apm=apm)
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=2048, temperature=0.2,
    )
