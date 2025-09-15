"""Photo editor CLI built on Pillow with logging and safe operations.

Install Pillow: pip install Pillow
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)


class PhotoEditError(RuntimeError):
    """Raised when photo editing operations fail."""


def open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
        return img
    except FileNotFoundError as ex:
        raise PhotoEditError(f"Input not found: {path}") from ex
    except Exception as ex:  # noqa: BLE001
        raise PhotoEditError(f"Failed to open image '{path}': {ex}") from ex


def save_image(img: Image.Image, path: Path, quality: Optional[int] = None) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs: dict[str, Any] = {}
        if quality is not None:
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        img.save(path, **save_kwargs)
    except Exception as ex:  # noqa: BLE001
        raise PhotoEditError(f"Failed to save image to '{path}': {ex}") from ex


def cmd_crop(
    input_path: Path, output_path: Path, left: int, top: int, right: int, bottom: int
) -> None:
    img = open_image(input_path)
    if right <= left or bottom <= top:
        raise PhotoEditError("Invalid crop box: ensure right>left and bottom>top")
    cropped = img.crop((left, top, right, bottom))
    save_image(cropped, output_path)


def cmd_resize(
    input_path: Path, output_path: Path, width: int, height: int, keep_aspect: bool
) -> None:
    if width <= 0 or height <= 0:
        raise PhotoEditError("Width and height must be positive")
    img = open_image(input_path)
    if keep_aspect:
        img = img.copy()
        img.thumbnail((width, height), resample=Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)  # type: ignore[attr-defined]
        save_image(img, output_path)
    else:
        resized = img.resize((width, height), resample=Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)  # type: ignore[attr-defined]
        save_image(resized, output_path)


def cmd_flip(input_path: Path, output_path: Path, direction: str) -> None:
    img = open_image(input_path)
    if direction == "horizontal":
        flipped = img.transpose(getattr(Image, "FLIP_LEFT_RIGHT"))
    elif direction == "vertical":
        flipped = img.transpose(getattr(Image, "FLIP_TOP_BOTTOM"))
    else:
        raise PhotoEditError("direction must be 'horizontal' or 'vertical'")
    save_image(flipped, output_path)


def cmd_rotate(
    input_path: Path, output_path: Path, degrees: float, expand: bool
) -> None:
    img = open_image(input_path)
    rotated = img.rotate(degrees, expand=expand, resample=Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC)  # type: ignore[attr-defined]
    save_image(rotated, output_path)


def cmd_blur(input_path: Path, output_path: Path, radius: float) -> None:
    img = open_image(input_path)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    save_image(blurred, output_path)


def cmd_text(
    input_path: Path,
    output_path: Path,
    text: str,
    x: int,
    y: int,
    color: Tuple[int, int, int],
    font_path: Optional[Path],
    size: int,
) -> None:
    img = open_image(input_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = (
            ImageFont.truetype(str(font_path), size)
            if font_path
            else ImageFont.load_default()
        )
    except Exception:
        font = ImageFont.load_default()
    draw.text((x, y), text, font=font, fill=color + (255,))
    save_image(img.convert("RGB"), output_path)


def cmd_grayscale(input_path: Path, output_path: Path) -> None:
    img = open_image(input_path)
    gray = img.convert("L")
    save_image(gray, output_path)


def cmd_sharpen(input_path: Path, output_path: Path) -> None:
    img = open_image(input_path)
    sharp = img.filter(ImageFilter.SHARPEN)
    save_image(sharp, output_path)


def cmd_merge(
    input1: Path, input2: Path, output_path: Path, alpha: float, fit: bool
) -> None:
    if not (0.0 <= alpha <= 1.0):
        raise PhotoEditError("alpha must be in [0,1]")
    img1 = open_image(input1).convert("RGBA")
    img2 = open_image(input2).convert("RGBA")
    if fit and img2.size != img1.size:
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore[attr-defined]
        img2 = img2.resize(img1.size, resample=resample)
    if img2.size != img1.size:
        raise PhotoEditError("Images must be same size (or use --fit)")
    blended = Image.blend(img1, img2, alpha)
    save_image(blended.convert("RGB"), output_path)


def parse_color(color_str: str) -> Tuple[int, int, int]:
    try:
        parts = [int(p) for p in color_str.split(",")]
        if len(parts) != 3 or any(p < 0 or p > 255 for p in parts):
            raise ValueError
        return parts[0], parts[1], parts[2]
    except Exception as ex:  # noqa: BLE001
        raise argparse.ArgumentTypeError(
            "Color must be 'R,G,B' with 0..255 values"
        ) from ex


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Photo editor operations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # crop
    p_crop = sub.add_parser("crop", help="Crop an image")
    p_crop.add_argument("input", type=Path)
    p_crop.add_argument("output", type=Path)
    p_crop.add_argument("left", type=int)
    p_crop.add_argument("top", type=int)
    p_crop.add_argument("right", type=int)
    p_crop.add_argument("bottom", type=int)

    # resize
    p_resize = sub.add_parser("resize", help="Resize an image")
    p_resize.add_argument("input", type=Path)
    p_resize.add_argument("output", type=Path)
    p_resize.add_argument("width", type=int)
    p_resize.add_argument("height", type=int)
    p_resize.add_argument("--keep-aspect", action="store_true")

    # flip
    p_flip = sub.add_parser("flip", help="Flip an image")
    p_flip.add_argument("input", type=Path)
    p_flip.add_argument("output", type=Path)
    p_flip.add_argument("direction", choices=["horizontal", "vertical"])

    # rotate
    p_rotate = sub.add_parser("rotate", help="Rotate an image")
    p_rotate.add_argument("input", type=Path)
    p_rotate.add_argument("output", type=Path)
    p_rotate.add_argument("degrees", type=float)
    p_rotate.add_argument("--expand", action="store_true")

    # blur
    p_blur = sub.add_parser("blur", help="Gaussian blur")
    p_blur.add_argument("input", type=Path)
    p_blur.add_argument("output", type=Path)
    p_blur.add_argument("--radius", type=float, default=2.0)

    # text
    p_text = sub.add_parser("text", help="Draw text on image")
    p_text.add_argument("input", type=Path)
    p_text.add_argument("output", type=Path)
    p_text.add_argument("text", type=str)
    p_text.add_argument("x", type=int)
    p_text.add_argument("y", type=int)
    p_text.add_argument("--color", type=parse_color, default=(255, 0, 0))
    p_text.add_argument("--font", type=Path)
    p_text.add_argument("--size", type=int, default=20)

    # grayscale
    p_gray = sub.add_parser("grayscale", help="Convert to grayscale")
    p_gray.add_argument("input", type=Path)
    p_gray.add_argument("output", type=Path)

    # sharpen
    p_sharp = sub.add_parser("sharpen", help="Sharpen image")
    p_sharp.add_argument("input", type=Path)
    p_sharp.add_argument("output", type=Path)

    # merge
    p_merge = sub.add_parser("merge", help="Blend two images")
    p_merge.add_argument("input1", type=Path)
    p_merge.add_argument("input2", type=Path)
    p_merge.add_argument("output", type=Path)
    p_merge.add_argument("--alpha", type=float, default=0.5)
    p_merge.add_argument(
        "--fit", action="store_true", help="Resize second image to match first"
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

    try:
        if args.command == "crop":
            cmd_crop(
                args.input, args.output, args.left, args.top, args.right, args.bottom
            )
        elif args.command == "resize":
            cmd_resize(
                args.input, args.output, args.width, args.height, args.keep_aspect
            )
        elif args.command == "flip":
            cmd_flip(args.input, args.output, args.direction)
        elif args.command == "rotate":
            cmd_rotate(args.input, args.output, args.degrees, args.expand)
        elif args.command == "blur":
            cmd_blur(args.input, args.output, args.radius)
        elif args.command == "text":
            cmd_text(
                args.input,
                args.output,
                args.text,
                args.x,
                args.y,
                args.color,
                args.font,
                args.size,
            )
        elif args.command == "grayscale":
            cmd_grayscale(args.input, args.output)
        elif args.command == "sharpen":
            cmd_sharpen(args.input, args.output)
        elif args.command == "merge":
            cmd_merge(args.input1, args.input2, args.output, args.alpha, args.fit)
        else:
            logger.error("Unknown command")
            return 2
    except PhotoEditError as ex:
        logger.error(str(ex))
        return 1

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
