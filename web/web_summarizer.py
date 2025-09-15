"""Web page summarizer CLI with logging and backend options.

Fetches a URL, extracts text, optionally truncates, and summarizes using
Hugging Face pipeline or TheTextAPI fallback.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebSummarizerError(RuntimeError):
    """Raised when fetching or summarization fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a web page via Hugging Face or TheTextAPI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", type=str, help="URL to summarize")
    parser.add_argument("--backend", choices=["hf", "api"], default="hf")
    parser.add_argument(
        "--api-url", type=str, default="https://app.thetextapi.com/text/summarize"
    )
    parser.add_argument(
        "--api-key", type=str, help="API key for TheTextAPI (or TEXTAPI_KEY env)"
    )
    parser.add_argument("--hf-model", type=str, default="facebook/bart-large-cnn")
    parser.add_argument(
        "--max-chars", type=int, default=5000, help="Max characters from page text"
    )
    parser.add_argument(
        "--output", type=Path, help="Write summary to file instead of stdout"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as ex:
        raise WebSummarizerError(f"Failed to fetch URL: {ex}") from ex


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: List[str] = []
    for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
        parts.append(tag.get_text(" ", strip=True))
    return "\n".join(parts)


def summarize_hf(text: str, model_name: str) -> str:
    try:
        from transformers import pipeline  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        raise WebSummarizerError(
            "transformers not installed. Run: pip install transformers"
        ) from ex
    try:
        summarizer = pipeline("summarization", model=model_name)  # type: ignore[call-arg]
        result = summarizer(text)
        return str(result[0]["summary_text"])  # type: ignore[index]
    except Exception as ex:  # noqa: BLE001
        raise WebSummarizerError(f"HF summarization failed: {ex}") from ex


def summarize_api(text: str, api_url: str, api_key_opt: Optional[str]) -> str:
    api_key = api_key_opt or os.getenv("TEXTAPI_KEY")
    if not api_key:
        raise WebSummarizerError(
            "Missing API key. Provide --api-key or set TEXTAPI_KEY env var."
        )
    try:
        resp = requests.post(
            api_url,
            headers={"Content-Type": "application/json", "apikey": api_key},
            json={"text": text},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        summary = data.get("summary")
        if not isinstance(summary, str):
            raise WebSummarizerError("API did not return a 'summary' string")
        return summary
    except requests.RequestException as ex:
        raise WebSummarizerError(f"API request failed: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        html = fetch_html(args.url)
        text = extract_text(html)
        if args.max_chars > 0:
            text = text[: args.max_chars]
        if args.backend == "hf":
            summary = summarize_hf(text, args.hf_model)
        else:
            summary = summarize_api(text, args.api_url, args.api_key)
    except WebSummarizerError as ex:
        logger.error(str(ex))
        return 1

    if args.output:
        try:
            args.output.write_text(summary, encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write summary: {ex}")
            return 1
        logger.info(f"Wrote summary to {args.output}")
    else:
        print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
