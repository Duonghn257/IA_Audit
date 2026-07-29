"""Environment loading for Anthropic credentials."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    base_url: str | None  # None → SDK default


class ConfigError(RuntimeError):
    """Raised when required backend configuration is missing."""


def load_config() -> Config:
    """Load and validate Anthropic config from backend/.env."""
    # override=True: .env is the source of truth for this POC, even if the
    # launching shell already exports ANTHROPIC_* vars (e.g. Claude Code's own).
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL")
    endpoint = os.environ.get("ANTHROPIC_URI_ENDPOINT") or None

    missing = [n for n, v in {"ANTHROPIC_API_KEY": api_key,
                              "ANTHROPIC_MODEL": model}.items() if not v]
    if missing:
        raise ConfigError(
            f"missing required env var(s): {', '.join(missing)}"
        )

    # Azure AI Foundry publishes endpoints with '/v1/messages' already appended.
    # The Anthropic SDK appends it itself, so strip the suffix to avoid doubling.
    if endpoint:
        for suffix in ("/v1/messages", "/v1/messages/"):
            if endpoint.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                break

    return Config(api_key=api_key, model=model, base_url=endpoint)
