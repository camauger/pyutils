"""Sentiment analysis utility using TextBlob.

Provides a simple CLI to analyze sentiment from a string, a file, or stdin.

Examples:
  - Analyze a short text:
    python blobbing.py --text "Python is amazing!"

  - Analyze content from a file:
    python blobbing.py --file notes.txt

  - Pipe text via stdin:
    echo "I love this" | python blobbing.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from textblob import TextBlob

logger = logging.getLogger(__name__)


class SentimentAnalysisError(Exception):
    """Raised when sentiment analysis fails."""


@dataclass(frozen=True)
class SentimentResult:
    """Sentiment analysis result values.

    Polarity in [-1, 1], subjectivity in [0, 1].
    """

    polarity: float
    subjectivity: float


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for the sentiment analyzer."""
    parser = argparse.ArgumentParser(
        description="Analyze sentiment using TextBlob.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", type=str, help="Text to analyze")
    source.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def read_text_from_stdin() -> Optional[str]:
    """Read text from stdin if data is piped. Return None if stdin is a TTY."""
    if sys.stdin is None or sys.stdin.isatty():
        return None
    data = sys.stdin.read()
    return data


def load_text_from_file(path: Path) -> str:
    """Load UTF-8 text from a file, raising on errors."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise SentimentAnalysisError(f"Failed to read file '{path}': {ex}") from ex


def analyze_sentiment(text: str) -> SentimentResult:
    """Run TextBlob sentiment analysis on `text` and return results.

    Raises SentimentAnalysisError on failure.
    """
    if not text or not text.strip():
        raise SentimentAnalysisError("Empty text; provide non-empty input.")
    try:
        blob = TextBlob(text)
        sentiment_obj: Any = (
            blob.sentiment
        )  # sentiment is a cached_property; cast for typing
        return SentimentResult(
            polarity=float(sentiment_obj.polarity),
            subjectivity=float(sentiment_obj.subjectivity),
        )
    except Exception as ex:  # noqa: BLE001
        raise SentimentAnalysisError(f"Sentiment analysis failed: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    text: Optional[str] = None
    if args.text is not None:
        text = args.text
    elif args.file is not None:
        text = load_text_from_file(args.file)
    else:
        text = read_text_from_stdin()

    if text is None:
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    try:
        result = analyze_sentiment(text)
    except SentimentAnalysisError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        print(
            json.dumps(
                {"polarity": result.polarity, "subjectivity": result.subjectivity}
            )
        )
    else:
        logger.info(
            f"Polarity: {result.polarity:.3f}, Subjectivity: {result.subjectivity:.3f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
