"""Simple Google search CLI with logging and fallback.

Tries `pywhatkit.search` if available; falls back to opening the browser
with a constructed Google query URL.
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from typing import Optional
from urllib.parse import quote_plus

try:
    import pywhatkit as kit  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    kit = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a Google search for the given query.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", type=str, help="Search query string")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def build_google_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def perform_search(query: str) -> None:
    # Try pywhatkit first
    if kit is not None:
        try:
            search_func = getattr(kit, "search", None)
            if callable(search_func):
                search_func(query)
                logger.info("Opened Google search via pywhatkit.")
                return
        except Exception as ex:  # noqa: BLE001
            logger.debug(f"pywhatkit search failed: {ex}")

    # Fallback to webbrowser
    url = build_google_url(query)
    opened = webbrowser.open(url)
    logger.info(f"Opened: {url}" if opened else f"Please open manually: {url}")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    if not args.query.strip():
        logger.error("Empty query provided.")
        return 2

    perform_search(args.query)
    return 0


if __name__ == "__main__":
    sys.exit(main())
