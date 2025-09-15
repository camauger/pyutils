"""Clipboard monitor CLI: log changes with interval, timestamps, and logging.

Requires `pyperclip` for cross-platform clipboard access.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from time import perf_counter, sleep
from typing import Optional

try:
    import pyperclip  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    pyperclip = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class ClipboardError(RuntimeError):
    """Raised when clipboard operations fail or backend is unavailable."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor clipboard and append new contents to a log file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("clipboard_log.txt"),
        help="Output log file (UTF-8)",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Polling interval in seconds"
    )
    parser.add_argument(
        "--timestamp", action="store_true", help="Prefix entries with an ISO timestamp"
    )
    parser.add_argument(
        "--once", action="store_true", help="Capture one change then exit"
    )
    parser.add_argument(
        "--duration", type=float, help="Stop after N seconds (optional)"
    )
    parser.add_argument(
        "--strip", action="store_true", help="Strip trailing newlines before logging"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def get_clip_text() -> str:
    if pyperclip is None:
        raise ClipboardError("pyperclip is not installed. Run: pip install pyperclip")
    try:
        return str(pyperclip.paste())
    except Exception as ex:  # noqa: BLE001
        raise ClipboardError(f"Failed to read from clipboard: {ex}") from ex


def format_entry(text: str, add_timestamp: bool) -> str:
    if add_timestamp:
        from datetime import datetime

        ts = datetime.now().isoformat(timespec="seconds")
        return f"[{ts}] {text}\n"
    return f"{text}\n"


def monitor_clipboard(
    output: Path,
    interval: float,
    timestamp: bool,
    once: bool,
    duration: Optional[float],
    strip_newlines: bool,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)

    start = perf_counter()
    last_text: Optional[str] = None
    changes = 0

    try:
        while True:
            if duration is not None and (perf_counter() - start) >= duration:
                logger.info("Duration reached; exiting.")
                break

            try:
                current = get_clip_text()
            except ClipboardError as ex:
                logger.error(str(ex))
                return 1

            candidate = current.rstrip("\r\n") if strip_newlines else current
            if candidate != last_text:
                try:
                    with output.open("a", encoding="utf-8") as log:
                        log.write(format_entry(candidate, timestamp))
                    changes += 1
                    logger.info(f"Logged change #{changes} ({len(candidate)} chars)")
                except Exception as ex:  # noqa: BLE001
                    logger.error(f"Failed to write log: {ex}")
                    return 1
                last_text = candidate
                if once:
                    break

            sleep(max(0.05, interval))
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    return 0


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    return monitor_clipboard(
        output=args.output,
        interval=args.interval,
        timestamp=args.timestamp,
        once=args.once,
        duration=args.duration,
        strip_newlines=args.strip,
    )


if __name__ == "__main__":
    sys.exit(main())
