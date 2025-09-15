"""Convert text to a handwriting-style image using pywhatkit.

CLI supports input via --text, --file, or stdin, with configurable RGB color
and output path. Falls back gracefully if the backend is unavailable.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    import pywhatkit as kit  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    kit = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class HandwritingError(RuntimeError):
    """Raised when handwriting image generation fails."""


def parse_rgb(rgb_str: str) -> Tuple[int, int, int]:
    parts = rgb_str.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("RGB must be 'R,G,B' with 3 integers")
    try:
        r, g, b = (int(p.strip()) for p in parts)
    except ValueError as ex:
        raise argparse.ArgumentTypeError("RGB values must be integers") from ex
    for v in (r, g, b):
        if not (0 <= v <= 255):
            raise argparse.ArgumentTypeError("RGB values must be in [0,255]")
    return r, g, b


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render text to a handwriting-style PNG using pywhatkit.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", type=str, help="Text to render")
    source.add_argument("--file", type=Path, help="Path to a UTF-8 text file")
    parser.add_argument(
        "--rgb",
        type=parse_rgb,
        default=(0, 0, 255),
        help="Ink color as 'R,G,B' (0-255)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("handwriting.png"),
        help="Output PNG file path",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_text_from_stdin() -> Optional[str]:
    if sys.stdin is None or sys.stdin.isatty():
        return None
    return sys.stdin.read()


def load_text_from_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise HandwritingError(f"Failed to read file '{path}': {ex}") from ex


def render_handwriting(text: str, save_to: Path, rgb: Tuple[int, int, int]) -> None:
    if kit is None:
        raise HandwritingError(
            "pywhatkit is not installed or unavailable; cannot render handwriting."
        )
    try:
        func: Any = getattr(kit, "text_to_handwriting", None)
        if not callable(func):
            raise HandwritingError("pywhatkit.text_to_handwriting is not available")
        func(text, rgb=rgb, save_to=str(save_to))
    except Exception as ex:  # noqa: BLE001
        raise HandwritingError(f"Handwriting rendering failed: {ex}") from ex


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
            text = load_text_from_file(args.file)
        except HandwritingError as ex:
            logger.error(str(ex))
            return 2
    else:
        text = read_text_from_stdin()

    if text is None or not text.strip():
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    try:
        render_handwriting(text, args.output, args.rgb)
    except HandwritingError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Saved handwriting image to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
