"""OpenAI API CLI: chat or completion with env/flag API key and logging.

Supports reading prompt from --prompt, --file, or stdin. Tries the modern
client API; falls back to legacy if needed.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OpenAIError(RuntimeError):
    """Raised when OpenAI API operations fail."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query OpenAI via chat or completion.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--prompt", type=str, help="Prompt text")
    src.add_argument("--file", type=Path, help="Read prompt from UTF-8 file")

    parser.add_argument(
        "--system",
        type=str,
        default="You are a helpful assistant.",
        help="System prompt for chat mode",
    )
    parser.add_argument(
        "--mode", choices=["chat", "completion"], default="chat", help="API mode to use"
    )
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model name")
    parser.add_argument(
        "--temperature", type=float, default=0.3, help="Sampling temperature"
    )
    parser.add_argument("--max-tokens", type=int, default=256, help="Max new tokens")
    parser.add_argument("--top-p", type=float, default=1.0, help="Nucleus sampling p")
    parser.add_argument(
        "--api-key", type=str, help="API key (defaults to OPENAI_API_KEY env)"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_prompt(prompt: Optional[str], file: Optional[Path]) -> Optional[str]:
    if prompt is not None:
        return prompt
    if file is not None:
        try:
            return file.read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            raise OpenAIError(f"Failed to read prompt file '{file}': {ex}") from ex
    if sys.stdin is not None and not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def get_api_key(explicit: Optional[str]) -> str:
    key = explicit or os.getenv("OPENAI_API_KEY")
    if not key:
        raise OpenAIError(
            "Missing API key. Provide --api-key or set OPENAI_API_KEY env var."
        )
    return key


def call_openai(
    api_key: str,
    mode: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
) -> str:
    # Try modern client first
    try:
        from openai import OpenAI  # type: ignore[import-not-found]

        client: Any = OpenAI(api_key=api_key)
        if mode == "chat":
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            text = (resp.choices[0].message.content or "").strip()
        else:
            # Some models support legacy-style completions in the new client
            resp = client.completions.create(
                model=model,
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            text = (resp.choices[0].text or "").strip()
        return text
    except Exception as modern_ex:  # noqa: BLE001
        logger.debug(f"Modern client failed, trying legacy API: {modern_ex}")

    # Fallback: legacy API
    try:
        import openai as legacy  # type: ignore[import-not-found]

        legacy.api_key = api_key  # type: ignore[attr-defined]
        if mode == "chat":
            # Legacy chat
            resp = legacy.ChatCompletion.create(  # type: ignore[attr-defined]
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            text = (resp["choices"][0]["message"]["content"] or "").strip()
        else:
            resp = legacy.Completion.create(  # type: ignore[attr-defined]
                model=model,
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            text = (resp["choices"][0]["text"] or "").strip()
        return text
    except Exception as legacy_ex:  # noqa: BLE001
        raise OpenAIError(f"OpenAI API call failed: {legacy_ex}") from legacy_ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        prompt = read_prompt(args.prompt, args.file)
        if not prompt:
            logger.error("No prompt provided. Use --prompt, --file, or pipe via stdin.")
            return 2
        api_key = get_api_key(args.api_key)
        output = call_openai(
            api_key=api_key,
            mode=args.mode,
            model=args.model,
            system_prompt=args.system,
            user_prompt=prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            top_p=args.top_p,
        )
    except OpenAIError as ex:
        logger.error(str(ex))
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
