"""Step 4 -- LLM styling pass.

Produces a JSON style spec that the renderer consumes to match the template
appearance (colors, fonts, paragraph spacing). Inputs:
 - Formatting Guidelines (prose rules)
 - Template analysis (ground-truth palette extracted from template.docx)
 - Draft (for context about what elements exist)
"""
from __future__ import annotations

import json
from typing import Any

import anthropic

from ..context import wrap
from ..llm import LLMResult, call_json

SYSTEM = (
    "You produce a JSON style specification for a DOCX renderer. "
    "Reconcile the prose rules in <GUIDELINES> with the concrete palette "
    "observed in <TEMPLATE_ANALYSIS>. Where they conflict, prefer the "
    "template's actual values (the template is ground truth). "
    "Hex colors must be 6 uppercase characters with no '#'."
)

USER_TEMPLATE = """{guidelines_block}

{template_block}

{draft_block}

Return a JSON object with this exact shape:
{{
  "page": {{
    "orientation": "landscape" | "portrait",
    "size": "A4",
    "margin_inches": {{"left": <float>, "right": <float>, "top": <float>, "bottom": <float>}},
    "header_distance_inches": <float, distance from top edge to header text>,
    "footer_distance_inches": <float, distance from bottom edge to footer text>,
    "page_break_type": "section_next_page" | "page"
  }},
  "fonts": {{
    "body":      {{"family": "Arial", "size_pt": 10}},
    "exception": {{"family": "Arial", "size_pt": 9}}
  }},
  "paragraph_spacing": {{
    "body":      {{"before_pt": 6, "after_pt": 6, "line_at_least_pt": 13}},
    "exception": {{"before_pt": 3, "after_pt": 3, "line_at_least_pt": 13}}
  }},
  "colors": {{
    "summary_header_bg":     "<hex>",
    "issue_table_header_bg": "<hex>",
    "category_banner_bg":    "<hex>",
    "risk_banner_bg":        "<hex>",
    "risk_level_marker": {{
      "High":   "<hex>",
      "Medium": "<hex>",
      "Low":    "<hex>"
    }}
  }},
  "notes": "<1-2 sentences: where template and guidelines agreed / disagreed>"
}}

Rules:
- orientation MUST be "landscape" (landscape A4 is the house default for this report).
- size MUST be "A4".
- Fill each color from <TEMPLATE_ANALYSIS>.fill_colors based on the text that
  appears in those cells (e.g. a cell containing "S/N" or "Findings" marks the
  issue table header; "A." / "B." marks category banners; "HIGH RISK" or
  "MEDIUM RISK" marks the risk banner; the "X" columns under "High"/"Medium"/"Low"
  headers mark the per-risk markers; a cell under "Issues"/"Audit Risk Level"
  header marks the summary index header).
- When only one risk level is observed in the template, infer the other two
  from <GUIDELINES> section 24 (Content Page) which uses red/amber/green
  convention: High = red tone, Medium = amber/orange, Low = green.
- Fonts and spacing should follow <GUIDELINES> sections 1 and 2.
- header_distance_inches and footer_distance_inches should follow <GUIDELINES>
  sections 18 and 19 (typically 0.49 inches for this house style).
- page_break_type MUST be "section_next_page" per <GUIDELINES> section 9,
  which explicitly forbids plain page breaks in issue logs.

Respond with JSON only, inside a ```json fenced block."""


def produce_style_spec(
    client: anthropic.Anthropic,
    model: str,
    *,
    guidelines: str,
    template_analysis: dict[str, Any],
    draft: list[dict[str, Any]],
) -> LLMResult:
    user = USER_TEMPLATE.format(
        guidelines_block=wrap("GUIDELINES", guidelines),
        template_block=wrap("TEMPLATE_ANALYSIS", json.dumps(template_analysis, indent=2)),
        draft_block=wrap("DRAFT", json.dumps(draft, indent=2)),
    )
    return call_json(
        client, model=model, system=SYSTEM, user=user,
        max_tokens=1024, temperature=0.0,
    )


DEFAULT_STYLE_SPEC: dict[str, Any] = {
    "page": {
        "orientation": "landscape",
        "size": "A4",
        "margin_inches": {"left": 1.0, "right": 1.0, "top": 1.0, "bottom": 1.0},
        "header_distance_inches": 0.49,
        "footer_distance_inches": 0.49,
        "page_break_type": "section_next_page",
    },
    "fonts": {
        "body":      {"family": "Arial", "size_pt": 10},
        "exception": {"family": "Arial", "size_pt": 9},
    },
    "paragraph_spacing": {
        "body":      {"before_pt": 6, "after_pt": 6, "line_at_least_pt": 13},
        "exception": {"before_pt": 3, "after_pt": 3, "line_at_least_pt": 13},
    },
    "colors": {
        "summary_header_bg":     "FADFA0",
        "issue_table_header_bg": "FFE599",
        "category_banner_bg":    "D9D9D9",
        "risk_banner_bg":        "FFF2CC",
        "risk_level_marker": {
            "High":   "C00000",
            "Medium": "FFC000",
            "Low":    "00B050",
        },
    },
    "notes": "Deterministic fallback derived from template.docx palette.",
}


def normalise_style_spec(
    spec: dict[str, Any] | None,
    template_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge LLM output over DEFAULT_STYLE_SPEC; force landscape A4.

    When `template_analysis` is provided, its `roled_colors` and margins are
    applied as overrides on top of the LLM output -- they are ground truth
    extracted from the actual template file.
    """
    import copy

    out = copy.deepcopy(DEFAULT_STYLE_SPEC)

    def _merge(dst: dict[str, Any], src: dict[str, Any]) -> None:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                _merge(dst[k], v)
            else:
                dst[k] = v

    if spec:
        _merge(out, spec)

    # Template-derived overrides: trust observed values over LLM guesses.
    if template_analysis:
        roled = template_analysis.get("roled_colors", {}) or {}
        for role, color in roled.items():
            if role.startswith("risk_level_marker."):
                lvl = role.split(".", 1)[1]
                out["colors"]["risk_level_marker"][lvl] = color
            elif role in out["colors"]:
                out["colors"][role] = color
        mi = template_analysis.get("page", {}).get("margin_inches")
        if isinstance(mi, (int, float)) and mi > 0:
            out["page"]["margin_inches"] = {
                "left": mi, "right": mi, "top": mi, "bottom": mi,
            }

    # Hard defaults the user mandated.
    out["page"]["orientation"] = "landscape"
    out["page"]["size"] = "A4"
    # Floor page_break_type to the Guideline-mandated value. LLMs occasionally
    # emit "page" under template pressure; §9 forbids it, so clamp here.
    if out["page"].get("page_break_type") not in ("section_next_page", "page"):
        out["page"]["page_break_type"] = "section_next_page"
    for key in ("header_distance_inches", "footer_distance_inches"):
        v = out["page"].get(key)
        if not isinstance(v, (int, float)) or v <= 0:
            out["page"][key] = 0.49
    return out
