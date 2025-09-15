"""Watermarker CLI using Pillow with text/image options and logging.

Install Pillow: pip install Pillow
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class WatermarkError(RuntimeError):
    """Raised when watermark operations fail."""


def open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
        return img
    except FileNotFoundError as ex:
        raise WatermarkError(f"Input not found: {path}") from ex
    except Exception as ex:  # noqa: BLE001
        raise WatermarkError(f"Failed to open image '{path}': {ex}") from ex


def resolve_font(font_path: Optional[Path], size: int) -> ImageFont.ImageFont:
    try:
        if font_path is not None:
            return ImageFont.truetype(str(font_path), size)  # type: ignore[return-value]
    except Exception:
        logger.warning("Failed to load truetype font; falling back to default.")
    default_font: ImageFont.ImageFont = ImageFont.load_default()  # type: ignore[assignment]
    return default_font


def compute_position(
    base_size: Tuple[int, int],
    mark_size: Tuple[int, int],
    anchor: str,
    margin: Tuple[int, int],
) -> Tuple[int, int]:
    bw, bh = base_size
    mw, mh = mark_size
    mx, my = margin
    anchor = anchor.lower()
    if anchor == "top-left":
        return mx, my
    if anchor == "top-right":
        return max(0, bw - mw - mx), my
    if anchor == "bottom-left":
        return mx, max(0, bh - mh - my)
    if anchor == "center":
        return max(0, (bw - mw) // 2), max(0, (bh - mh) // 2)
    # bottom-right default
    return max(0, bw - mw - mx), max(0, bh - mh - my)


def add_text_watermark(
    input_path: Path,
    output_path: Path,
    text: str,
    font_path: Optional[Path],
    size: int,
    color: Tuple[int, int, int, int],
    anchor: str,
    margin: Tuple[int, int],
) -> None:
    base = open_image(input_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    font = resolve_font(font_path, size)
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), text, font=font)
    mw, mh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = compute_position(base.size, (mw, mh), anchor, margin)
    draw.text((x, y), text, font=font, fill=color)
    result = Image.alpha_composite(base, overlay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output_path)


def add_image_watermark(
    input_path: Path,
    output_path: Path,
    watermark_path: Path,
    opacity: int,
    anchor: str,
    margin: Tuple[int, int],
    scale: float,
) -> None:
    if not (0 <= opacity <= 255):
        raise WatermarkError("opacity must be in [0,255]")
    if scale <= 0:
        raise WatermarkError("scale must be > 0")
    base = open_image(input_path).convert("RGBA")
    mark = open_image(watermark_path).convert("RGBA")
    if scale != 1.0:
        new_size = (max(1, int(mark.width * scale)), max(1, int(mark.height * scale)))
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore[attr-defined]
        mark = mark.resize(new_size, resample=resample)
    # apply opacity
    if opacity < 255:
        r, g, b, a = mark.split()
        a = a.point(lambda p: int(p * (opacity / 255.0)))
        mark = Image.merge("RGBA", (r, g, b, a))
    x, y = compute_position(base.size, (mark.width, mark.height), anchor, margin)
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    overlay.paste(mark, (x, y), mark)
    result = Image.alpha_composite(base, overlay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output_path)


def parse_color(color_str: str) -> Tuple[int, int, int, int]:
    parts = color_str.split(",")
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError("Color must be 'R,G,B[,A]'")
    try:
        vals = [int(p.strip()) for p in parts]
    except ValueError as ex:
        raise argparse.ArgumentTypeError("Color components must be integers") from ex
    if any(v < 0 or v > 255 for v in vals):
        raise argparse.ArgumentTypeError("Color components must be in [0,255]")
    if len(vals) == 3:
        vals.append(128)
    return vals[0], vals[1], vals[2], vals[3]


def parse_margin(margin_str: str) -> Tuple[int, int]:
    parts = margin_str.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Margin must be 'x,y'")
    try:
        x, y = int(parts[0].strip()), int(parts[1].strip())
        if x < 0 or y < 0:
            raise ValueError
        return x, y
    except ValueError as ex:
        raise argparse.ArgumentTypeError(
            "Margin values must be non-negative integers"
        ) from ex


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add text or image watermark to an image.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_text = sub.add_parser("text", help="Add text watermark")
    p_text.add_argument("input", type=Path)
    p_text.add_argument("output", type=Path)
    p_text.add_argument("--text", required=True, help="Watermark text")
    p_text.add_argument("--font", type=Path, help="Path to TTF/OTF font")
    p_text.add_argument("--size", type=int, default=32)
    p_text.add_argument("--color", type=parse_color, default=(0, 0, 0, 128))
    p_text.add_argument(
        "--anchor",
        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        default="bottom-right",
    )
    p_text.add_argument("--margin", type=parse_margin, default=(16, 16))

    p_img = sub.add_parser("image", help="Add image watermark")
    p_img.add_argument("input", type=Path)
    p_img.add_argument("output", type=Path)
    p_img.add_argument(
        "--mark",
        required=True,
        type=Path,
        help="Path to watermark image (PNG with alpha recommended)",
    )
    p_img.add_argument("--opacity", type=int, default=128)
    p_img.add_argument(
        "--anchor",
        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        default="bottom-right",
    )
    p_img.add_argument("--margin", type=parse_margin, default=(16, 16))
    p_img.add_argument(
        "--scale", type=float, default=1.0, help="Scale factor for watermark image"
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
        if args.command == "text":
            add_text_watermark(
                input_path=args.input,
                output_path=args.output,
                text=args.text,
                font_path=args.font,
                size=args.size,
                color=args.color,
                anchor=args.anchor,
                margin=args.margin,
            )
        elif args.command == "image":
            add_image_watermark(
                input_path=args.input,
                output_path=args.output,
                watermark_path=args.mark,
                opacity=args.opacity,
                anchor=args.anchor,
                margin=args.margin,
                scale=args.scale,
            )
        else:
            logger.error("Unknown command")
            return 2
    except WatermarkError as ex:
        logger.error(str(ex))
        return 1

    logger.info("Watermark applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
