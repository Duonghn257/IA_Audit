"""Smoke-test the Anthropic API connection using values from .env."""

import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv


def main() -> int:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL")
    endpoint = os.environ.get("ANTHROPIC_URI_ENDPOINT")

    missing = [name for name, val in {
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_MODEL": model,
    }.items() if not val]
    if missing:
        print(f"Missing required env var(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    # The Anthropic SDK appends '/v1/messages' itself. If the configured endpoint
    # already includes that suffix (as Azure AI Foundry publishes it), strip it so
    # we don't end up POSTing to '.../v1/messages/v1/messages'.
    base_url = endpoint
    if base_url:
        for suffix in ("/v1/messages", "/v1/messages/"):
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
                break

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    print(f"Endpoint (env)    : {endpoint or '(unset)'}")
    print(f"Endpoint (in use) : {base_url or '(default) https://api.anthropic.com'}")
    print(f"Model             : {model}")
    print("Sending test message...\n")

    client = Anthropic(**client_kwargs)
    response = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[
            {"role": "user", "content": "Hello !"},
        ],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    print(f"Response : {text!r}")
    print(f"Stop     : {response.stop_reason}")
    print(f"Tokens   : in={response.usage.input_tokens} out={response.usage.output_tokens}")
    print("\nConnection OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
