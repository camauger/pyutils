"""Wikipedia facts CLI with logging and safe fetching.

Uses the `wikipedia` package if available; falls back to pywhatkit.info.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional

try:
    import wikipedia  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    wikipedia = None  # type: ignore[assignment]

try:
    import pywhatkit as kit  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    kit = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class WikiFactsError(RuntimeError):
    """Raised when fetching Wikipedia info fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a Wikipedia summary for a topic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("topic", type=str, help="Topic to search")
    parser.add_argument("--lines", type=int, default=3, help="Number of lines to show")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def fetch_summary(topic: str, lines: int) -> str:
    if wikipedia is not None:
        try:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(topic, sentences=lines)
            return summary
        except Exception as ex:  # noqa: BLE001
            logger.debug(f"wikipedia failed: {ex}")
    if kit is not None:
        func = getattr(kit, "info", None)
        if callable(func):
            try:
                func(topic, lines=lines)
                return ""
            except Exception as ex:  # noqa: BLE001
                raise WikiFactsError(f"pywhatkit.info failed: {ex}") from ex
    raise WikiFactsError("No backend available. Install 'wikipedia' or 'pywhatkit'.")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        text = fetch_summary(args.topic, args.lines)
    except WikiFactsError as ex:
        logger.error(str(ex))
        return 1

    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
