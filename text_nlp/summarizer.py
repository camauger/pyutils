"""Text summarizer CLI using TheTextAPI with optional HF fallback and logging.

Install: pip install requests transformers
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class SummarizerError(RuntimeError):
    """Raised when summarization fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize text via TheTextAPI or Hugging Face pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", type=str, help="Input text to summarize")
    src.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument("--backend", choices=["api", "hf"], default="api")
    parser.add_argument(
        "--api-url", type=str, default="https://app.thetextapi.com/text/summarize"
    )
    parser.add_argument("--api-key", type=str, help="API key (or TEXTAPI_KEY env)")
    parser.add_argument("--hf-model", type=str, default="facebook/bart-large-cnn")
    parser.add_argument(
        "--json", action="store_true", help="Output JSON with summary field"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_input(text: Optional[str], file: Optional[Path]) -> Optional[str]:
    if text is not None:
        return text
    if file is not None:
        try:
            return file.read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            raise SummarizerError(f"Failed to read file '{file}': {ex}") from ex
    if sys.stdin is not None and not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def summarize_api(text: str, api_url: str, api_key_opt: Optional[str]) -> str:
    api_key = api_key_opt or os.getenv("TEXTAPI_KEY")
    if not api_key:
        raise SummarizerError(
            "Missing API key. Provide --api-key or set TEXTAPI_KEY env var."
        )
    headers = {"Content-Type": "application/json", "apikey": api_key}
    payload: Dict[str, Any] = {"text": text}
    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        summary = data.get("summary")
        if not isinstance(summary, str):
            raise SummarizerError("API did not return a 'summary' string")
        return summary
    except requests.RequestException as ex:
        raise SummarizerError(f"API request failed: {ex}") from ex
    except ValueError as ex:
        raise SummarizerError(f"Invalid JSON response: {ex}") from ex


def summarize_hf(text: str, model_name: str) -> str:
    try:
        from transformers import pipeline  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        raise SummarizerError(
            "transformers not installed. Run: pip install transformers"
        ) from ex
    try:
        summarizer = pipeline("summarization", model=model_name)  # type: ignore[call-arg]
        result = summarizer(text)
        return str(result[0]["summary_text"])  # type: ignore[index]
    except Exception as ex:  # noqa: BLE001
        raise SummarizerError(f"HF summarization failed: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        text = read_input(args.text, args.file)
    except SummarizerError as ex:
        logger.error(str(ex))
        return 2

    if not text:
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    try:
        if args.backend == "api":
            summary = summarize_api(text, args.api_url, args.api_key)
        else:
            summary = summarize_hf(text, args.hf_model)
    except SummarizerError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        print(json.dumps({"summary": summary}, ensure_ascii=False))
    else:
        print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
