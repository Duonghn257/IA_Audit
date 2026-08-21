"""Step 3 — LLM self-critique of the draft."""
from __future__ import annotations

import json
from typing import Any

import anthropic

from app.ai.client import LLMResult, call_json
from app.rag.context import wrap

SYSTEM = (
    "You are an Internal Audit reviewer. You inspect a draft issue log "
    "against the audit scope, writing guidelines, and source evidence. "
    "You flag issues -- you do not rewrite them. Be specific: quote the "
    "exact problematic excerpt, and cite the <GUIDELINES> section number "
    "when flagging TONE_VIOLATION."
)

USER_TEMPLATE = """{scope_block}

{guidelines_block}

{sop_block}

{pu_block}

{draft_block}

Review each issue in <DRAFT>. Return JSON:
{{
  "issues": [
    {{"issue_id": "I-1",
     "flags": [
       {{"type": "SCOPE_BREACH" | "UNSUPPORTED_ASSERTION"
              | "TONE_VIOLATION"  | "WEAK_EVIDENCE",
        "severity": "low" | "medium" | "high",
        "excerpt": "<verbatim text from the draft>",
        "reason": "<one sentence; cite GUIDELINES section where applicable>"}}
     ]}}
  ],
  "summary": "<2-3 sentence overall assessment>"
}}

Flag type definitions:
- SCOPE_BREACH: content references entities or activities outside <SCOPE>'s
  audited_entities or audit_scope, or touches an out_of_scope_item.
- UNSUPPORTED_ASSERTION: a specific factual claim in "finding", "risk_impact",
  "root_cause", or "recommendation" cannot be traced to <SOP> or
  <PROCESS_UNDERSTANDING>. Do NOT flag general framing sentences (e.g.
  "The review process provides incomplete assurance"); only flag concrete
  factual claims (names, dates, amounts, quoted policy text, or cause
  statements) that lack a matching passage in the sources.
- TONE_VIOLATION: issue title conflicts with <GUIDELINES> section 13.
  Section 13 defines POSITIVE tone as constructive phrasings such as
  "X should be adhered to / enhanced / strengthened / complied with",
  "X could be strengthened", or imperative "Enhance X". Do NOT flag these
  as negative -- they are the approved house style (see <SAMPLES> headers
  e.g. "Procedures ... should be complied with", "SAP workflow ... could
  be strengthened", "Review procedures ... should be enhanced"). Flag only
  true negative phrasings: "Failure to X", "Non-compliance of X", "X was
  not done", "Lack of X". Sub-headers inside the finding MAY be negative
  (section 13 last bullet).
- WEAK_EVIDENCE: evidence_refs exist but do not substantiate the finding
  (wrong document, generic label without a section/sheet/page, or missing
  a critical claim in the finding).

If an issue is clean, return "flags": [].

Respond with JSON only, inside a ```json fenced block."""


def critique_draft(
    client: anthropic.Anthropic,
    model: str,
    *,
    constraints: dict[str, Any],
    guidelines: str,
    sop: str,
    process_understanding: str,
    draft: list[dict[str, Any]],
) -> LLMResult:
    user = USER_TEMPLATE.format(
        scope_block=wrap("SCOPE", json.dumps(constraints, indent=2)),
        guidelines_block=wrap("GUIDELINES", guidelines),
        sop_block=wrap("SOP", sop),
        pu_block=wrap("PROCESS_UNDERSTANDING", process_understanding),
        draft_block=wrap("DRAFT", json.dumps(draft, indent=2)),
    )
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=2048, temperature=0.1,
    )
