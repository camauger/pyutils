"""Image resizer CLI with aspect ratio options and logging.

Requires Pillow: pip install Pillow
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class ImageResizeError(RuntimeError):
    """Raised when image resizing fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resize an image with optional aspect ratio preservation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument("output", type=Path, help="Output image path")
    parser.add_argument("--width", type=int, help="Target width in pixels")
    parser.add_argument("--height", type=int, help="Target height in pixels")
    parser.add_argument(
        "--keep-aspect",
        action="store_true",
        help="Preserve aspect ratio; missing dimension is auto-computed",
    )
    parser.add_argument(
        "--fit-within",
        action="store_true",
        help="Scale to fit within width x height bounding box (requires both)",
    )
    parser.add_argument(
        "--resample",
        choices=["nearest", "bilinear", "bicubic", "lanczos"],
        default="lanczos",
        help="Resampling filter",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def get_resample_filter(name: str) -> Any:
    # Pillow 10+ uses Image.Resampling enum; earlier versions expose constants on Image
    resampling = getattr(Image, "Resampling", None)
    provider = resampling if resampling is not None else Image
    attr_map = {
        "nearest": "NEAREST",
        "bilinear": "BILINEAR",
        "bicubic": "BICUBIC",
        "lanczos": "LANCZOS",
    }
    attr = attr_map[name]
    return getattr(provider, attr)


def compute_target_size(
    original: Tuple[int, int],
    width: Optional[int],
    height: Optional[int],
    keep_aspect: bool,
    fit_within: bool,
) -> Tuple[int, int]:
    ow, oh = original
    if fit_within:
        if width is None or height is None:
            raise ImageResizeError("--fit-within requires both --width and --height")
        scale = min(width / ow, height / oh)
        return max(1, int(ow * scale)), max(1, int(oh * scale))

    if not keep_aspect:
        if width is None or height is None:
            raise ImageResizeError(
                "Provide both --width and --height or enable --keep-aspect"
            )
        return max(1, width), max(1, height)

    # keep aspect
    if width is None and height is None:
        raise ImageResizeError(
            "With --keep-aspect, specify at least one of --width/--height"
        )
    if width is None:
        scale = height / oh  # type: ignore[operator]
        return max(1, int(ow * scale)), max(1, height)  # type: ignore[arg-type]
    if height is None:
        scale = width / ow
        return max(1, width), max(1, int(oh * scale))
    # both provided: ignore aspect and use exact
    return max(1, width), max(1, height)


def resize_image(
    input_path: Path,
    output_path: Path,
    width: Optional[int],
    height: Optional[int],
    keep_aspect: bool,
    fit_within: bool,
    resample_name: str,
) -> None:
    try:
        with Image.open(input_path) as img:
            orig_size = (img.width, img.height)
            logger.info(f"Original size: {orig_size}")
            target = compute_target_size(
                orig_size, width, height, keep_aspect, fit_within
            )
            resample = get_resample_filter(resample_name)
            resized = img.resize(target, resample=resample)
            logger.info(f"Resized size: {resized.size}")
            # Ensure parent dir exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Preserve format if possible
            save_kwargs: dict[str, Any] = {}
            fmt = (img.format or "").upper()
            if fmt in {"JPEG", "JPG"}:
                save_kwargs["quality"] = 90
                save_kwargs["optimize"] = True
            resized.save(output_path, **save_kwargs)
    except Image.DecompressionBombError as ex:
        raise ImageResizeError(f"Image too large or suspicious: {ex}") from ex
    except FileNotFoundError as ex:
        raise ImageResizeError(f"Input not found: {input_path}") from ex
    except Exception as ex:  # noqa: BLE001
        raise ImageResizeError(f"Failed to resize image: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        resize_image(
            input_path=args.input,
            output_path=args.output,
            width=args.width,
            height=args.height,
            keep_aspect=args.keep_aspect,
            fit_within=args.fit_within,
            resample_name=args.resample,
        )
    except ImageResizeError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Saved resized image to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
