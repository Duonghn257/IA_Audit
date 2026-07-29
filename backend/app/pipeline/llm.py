"""Anthropic client wrapper, retry, and JSON extraction."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import anthropic

from app.core.config import Config


@dataclass
class LLMResult:
    data: Any              # parsed JSON (dict or list)
    input_tokens: int
    output_tokens: int
    raw_text: str


def make_client(cfg: Config) -> anthropic.Anthropic:
    kwargs: dict[str, Any] = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return anthropic.Anthropic(**kwargs)


def _call_with_retry(
    client: anthropic.Anthropic,
    *,
    max_attempts: int = 3,
    **kwargs: Any,
) -> anthropic.types.Message:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            last_err = e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                last_err = e
            else:
                raise
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
    assert last_err is not None
    raise last_err


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _strip_fence(text: str) -> str:
    """Extract JSON from a fenced block, or return text unchanged."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    # Fallback: find first balanced { or [
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return text.strip()


def _text_of(resp: anthropic.types.Message) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def call_json(
    client: anthropic.Anthropic,
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    temperature: float,
) -> LLMResult:
    """Send a messages.create call and parse a JSON response, with one retry on bad JSON."""
    messages = [{"role": "user", "content": user}]
    resp = _call_with_retry(
        client, model=model, system=system, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    text = _text_of(resp)
    try:
        data = json.loads(_strip_fence(text))
    except json.JSONDecodeError:
        # One-shot retry with a reminder
        messages = [
            {"role": "user", "content": user},
            {"role": "assistant", "content": text},
            {"role": "user", "content":
             "Your previous reply was not valid JSON. "
             "Respond with JSON only, inside a ```json fenced block."},
        ]
        resp = _call_with_retry(
            client, model=model, system=system, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )
        text = _text_of(resp)
        data = json.loads(_strip_fence(text))

    return LLMResult(
        data=data,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        raw_text=text,
    )
