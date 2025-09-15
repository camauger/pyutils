"""Collection helpers: tokenization and word counting utilities with CLI.

Provides reusable functions and an optional CLI for quick word counts.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def tokenize(text: str, lowercase: bool = True, strip_punct: bool = True) -> List[str]:
    """Split text into tokens.

    If `lowercase` is True, text is lowercased. If `strip_punct` is True,
    extract alphanumeric tokens using a simple regex.
    """
    processed = text.lower() if lowercase else text
    if strip_punct:
        return re.findall(r"\b\w+\b", processed)
    return processed.split()


def count_words(words: Iterable[str]) -> Dict[str, int]:
    """Return a frequency dictionary of words from an iterable."""
    return dict(Counter(words))


def count_words_in_text(
    text: str, lowercase: bool = True, strip_punct: bool = True
) -> Dict[str, int]:
    """Tokenize `text` and return word frequencies."""
    return count_words(tokenize(text, lowercase=lowercase, strip_punct=strip_punct))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Word counting utilities",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", type=str, help="Text to analyze")
    source.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument(
        "--no-lower", dest="lower", action="store_false", help="Disable lowercasing"
    )
    parser.set_defaults(lower=True)
    parser.add_argument(
        "--keep-punct",
        dest="strip_punct",
        action="store_false",
        help="Do not strip punctuation",
    )
    parser.set_defaults(strip_punct=True)
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


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
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to read file '{args.file}': {ex}")
            return 2
    else:
        if sys.stdin is not None and not sys.stdin.isatty():
            text = sys.stdin.read()

    if not text:
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    freqs = count_words_in_text(
        text, lowercase=args.lower, strip_punct=args.strip_punct
    )

    if args.json:
        print(json.dumps(freqs, ensure_ascii=False))
    else:
        for word, count in sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{word}\t{count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
