"""Deterministic validation checks for AI-drafted issues."""
from __future__ import annotations

import re
from typing import Any

# Short connective tokens that shouldn't be treated as identifying an entity.
_STOP_TOKENS = {"pte", "ltd", "the", "and", "of", "&"}


def _entity_tokens(entities: list[str]) -> set[str]:
    """Tokenise audited entities into matchable words (len >= 3, not stop).

    'CDL Zenith Pte Ltd' -> {'cdl', 'zenith'}
    'Lumina Grand'       -> {'lumina', 'grand'}
    """
    tokens: set[str] = set()
    for e in entities:
        for raw in re.split(r"[^A-Za-z0-9]+", e):
            t = raw.lower().strip()
            if len(t) < 3 or t in _STOP_TOKENS:
                continue
            tokens.add(t)
    return tokens


def check_evidence_refs(draft: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for issue in draft:
        refs = issue.get("evidence_refs") or []
        iid = issue.get("id", "?")
        if not refs:
            warnings.append(f"{iid}: missing evidence_refs")
            continue
        if any(not str(r).strip() for r in refs):
            warnings.append(f"{iid}: empty evidence_refs entry")
    return warnings


def check_scope(
    draft: list[dict[str, Any]],
    constraints: dict[str, Any],
) -> list[str]:
    entities = constraints.get("audited_entities", []) or []
    out_of_scope = [i.lower() for i in constraints.get("out_of_scope_items", [])]
    entity_tokens = _entity_tokens(entities)
    warnings: list[str] = []
    for issue in draft:
        iid = issue.get("id", "?")
        blob = " ".join([
            str(issue.get("title", "")),
            str(issue.get("finding", "")),
            str(issue.get("risk_impact", "")),
            str(issue.get("financial_impact", "")),
            str(issue.get("impact", "")),  # legacy
            str(issue.get("recommendation", "")),
            str(issue.get("root_cause", "")),
            str(issue.get("category", "")),
        ]).lower()
        for term in out_of_scope:
            if term and term in blob:
                warnings.append(
                    f"{iid}: mentions out-of-scope item '{term}'"
                )
        # Word-boundary check against any entity token (e.g. 'cdl', 'lumina').
        if entity_tokens:
            matched = any(
                re.search(rf"\b{re.escape(tok)}\b", blob) for tok in entity_tokens
            )
            if not matched:
                warnings.append(
                    f"{iid}: no audited_entity mentioned (possible scope drift)"
                )
    return warnings


def build_validation(
    draft: list[dict[str, Any]],
    constraints: dict[str, Any],
    llm_critique: dict[str, Any],
    context_truncated: bool,
) -> dict[str, Any]:
    """Assemble the merged validation.json payload."""
    warnings = check_evidence_refs(draft) + check_scope(draft, constraints)
    return {
        "context_truncated": context_truncated,
        "rule_based": {
            "passed": len(warnings) == 0,
            "warnings": warnings,
        },
        "llm_critique": llm_critique,
    }
