"""Remove image background via rembg with a typed CLI and logging.

Install: pip install rembg Pillow
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from rembg import remove  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    remove = None  # type: ignore[assignment]

from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)


class RemoveBgError(RuntimeError):
    """Raised when background removal fails or rembg is missing."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove background from an image using rembg.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument(
        "output", type=Path, help="Output image path (.png recommended)"
    )
    parser.add_argument(
        "--alpha",
        action="store_true",
        help="Ensure output has alpha channel (RGBA)",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def remove_background(input_path: Path, output_path: Path, ensure_alpha: bool) -> None:
    if remove is None:
        raise RemoveBgError("rembg is not installed. Run: pip install rembg")
    try:
        with Image.open(input_path) as inp:
            inp.load()
            out_raw: Any = remove(inp)  # type: ignore[operator]
            if isinstance(out_raw, (bytes, bytearray)):
                out_img = Image.open(BytesIO(out_raw))
            else:
                out_img = out_raw
            if ensure_alpha and getattr(out_img, "mode", None) != "RGBA":
                out_img = out_img.convert("RGBA")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_img.save(output_path)
    except FileNotFoundError as ex:
        raise RemoveBgError(f"Input not found: {input_path}") from ex
    except Exception as ex:  # noqa: BLE001
        raise RemoveBgError(f"Background removal failed: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        remove_background(args.input, args.output, args.alpha)
    except RemoveBgError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Saved output to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
