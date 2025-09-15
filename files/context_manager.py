"""Typed file context manager with logging and a small CLI demo.

Even though Python provides `open` as a context manager, this example shows
how to build a custom context manager using `@contextmanager` to centralize
defaults (like UTF-8 encoding) and cross-cutting concerns (e.g., logging).
"""

from __future__ import annotations

import argparse
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Iterator, Optional, Union

logger = logging.getLogger(__name__)


@contextmanager
def file_manager(
    filename: Union[str, Path],
    mode: str = "w",
    encoding: Optional[str] = "utf-8",
) -> Iterator[IO[Any]]:
    """Open a file with consistent defaults and ensure closure.

    If "b" is present in `mode`, `encoding` is ignored.
    """
    needs_binary = "b" in mode
    logger.debug(f"Opening file {filename!s} with mode={mode!r}")
    if needs_binary:
        f: IO[Any] = open(filename, mode)  # type: ignore[arg-type]
    else:
        f = open(filename, mode, encoding=encoding)  # type: ignore[arg-type]
    try:
        yield f
    finally:
        f.close()
        logger.debug(f"Closed file {filename!s}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write text to a file using a managed context.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Target file path")
    parser.add_argument("--text", type=str, help="Text to write; falls back to stdin")
    parser.add_argument(
        "--append", action="store_true", help="Append instead of overwrite"
    )
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

    text: Optional[str] = args.text
    if text is None and sys.stdin is not None and not sys.stdin.isatty():
        text = sys.stdin.read()

    if not text:
        logger.error("No input provided. Use --text or pipe via stdin.")
        return 2

    mode = "a" if args.append else "w"
    try:
        with file_manager(args.path, mode=mode, encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
        logger.info(f"Wrote {len(text)} chars to {args.path}")
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to write to {args.path}: {ex}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
