"""Contact sheet generator CLI.

Create contact sheets from a folder of images.

Features
- Grid layout with configurable columns/rows
- Thumbnail size, spacing, margins, background color
- Optional filename labels
- Recursive folder scan with include/exclude globs
- Outputs PNG/JPEG pages or a single PDF

Examples
- Basic PNG page(s):
  python -m images.image_contact_sheet ./photos --cols 6 --rows 5 --thumb 320x240 --spacing 8 --bg "#111111" --labels --out out/contact.png

- Multipage PDF with recursion and includes:
  python -m images.image_contact_sheet ./photos --recursive --include "*.jpg" --cols 5 --rows 6 --thumb 256x256 --labels --out out/contacts.pdf
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple, cast

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


@dataclass
class Layout:
    columns: int
    rows: int
    thumb_width: int
    thumb_height: int
    spacing: int
    margin: int
    label_height: int


@dataclass
class PageResult:
    page_index: int
    image_count: int
    path: Optional[Path]


def parse_size(value: str) -> Tuple[int, int]:
    if "x" not in value:
        raise argparse.ArgumentTypeError("Size must be WIDTHxHEIGHT, e.g. 320x240")
    w, h = value.lower().split("x", 1)
    return int(w), int(h)


def parse_color(value: str) -> Tuple[int, int, int]:
    v = value.strip()
    if v.startswith("#"):
        v = v[1:]
    if len(v) == 6:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    raise argparse.ArgumentTypeError("Color must be hex like #RRGGBB")


def parse_arguments() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build image contact sheets from a folder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("root", type=Path, help="Folder with images")
    p.add_argument("--cols", type=int, default=5, help="Columns per page")
    p.add_argument("--rows", type=int, default=6, help="Rows per page")
    p.add_argument(
        "--thumb", type=parse_size, default=(256, 256), help="Thumbnail size WxH"
    )
    p.add_argument("--spacing", type=int, default=8, help="Spacing between thumbs (px)")
    p.add_argument("--margin", type=int, default=24, help="Outer margin (px)")
    p.add_argument(
        "--label-height", type=int, default=24, help="Label text area height (px)"
    )
    p.add_argument(
        "--bg",
        type=parse_color,
        default=(20, 20, 20),
        help="Background color (#RRGGBB)",
    )
    p.add_argument("--font", type=Path, help="Optional TTF font for labels")
    p.add_argument("--font-size", type=int, default=14, help="Label font size")
    p.add_argument(
        "--labels", action="store_true", help="Draw filename labels under thumbnails"
    )

    sel = p.add_argument_group("Selection")
    sel.add_argument("--recursive", action="store_true")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )

    out = p.add_argument_group("Output")
    out.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output file (PNG/JPEG for images, PDF for multi-page)",
    )

    p.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return p.parse_args()


def iter_image_files(root: Path, recursive: bool) -> Iterator[Path]:
    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            base = Path(dirpath)
            for name in filenames:
                p = base / name
                if p.suffix.lower() in IMAGE_EXTS:
                    yield p
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p


def matches_filters(
    path: Path, base: Path, include: Sequence[str], exclude: Sequence[str]
) -> bool:
    rel = str(path.relative_to(base))
    name = path.name
    if include:
        if not any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in include
        ):
            return False
    if exclude:
        if any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in exclude
        ):
            return False
    return True


def load_font(font_path: Optional[Path], size: int) -> ImageFont.ImageFont:
    try:
        if font_path is not None and font_path.exists():
            return cast(ImageFont.ImageFont, ImageFont.truetype(str(font_path), size))
    except Exception as e:
        logger.warning(f"Failed to load font {font_path}: {e}")
    return cast(ImageFont.ImageFont, ImageFont.load_default())


def build_pages(
    images: List[Path],
    layout: Layout,
    bg: Tuple[int, int, int],
    draw_labels: bool,
    font: ImageFont.ImageFont,
) -> List[Image.Image]:
    cols, rows = layout.columns, layout.rows
    tw, th = layout.thumb_width, layout.thumb_height
    spacing, margin, label_h = (
        layout.spacing,
        layout.margin,
        layout.label_height if draw_labels else 0,
    )

    cell_w = tw
    cell_h = th + (label_h if draw_labels else 0)

    page_w = margin * 2 + cols * cell_w + (cols - 1) * spacing
    page_h = margin * 2 + rows * cell_h + (rows - 1) * spacing

    pages: List[Image.Image] = []

    def resize_thumb(img: Image.Image) -> Image.Image:
        resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore[attr-defined]
        return img.resize((tw, th), resample=resample)

    index = 0
    n = len(images)
    while index < n:
        canvas = Image.new("RGB", (page_w, page_h), color=bg)
        draw = ImageDraw.Draw(canvas)
        for r in range(rows):
            for c in range(cols):
                if index >= n:
                    break
                x = margin + c * (cell_w + spacing)
                y = margin + r * (cell_h + spacing)
                try:
                    with Image.open(images[index]) as im:
                        im = im.convert("RGB")
                        thumb = resize_thumb(im)
                        canvas.paste(thumb, (x, y))
                    if draw_labels:
                        text = images[index].name
                        tx = x + 4
                        ty = y + th + 2
                        draw.text((tx, ty), text, fill=(230, 230, 230), font=font)
                except Exception as e:
                    logger.warning(f"Skip {images[index]}: {e}")
                index += 1
        pages.append(canvas)
    return pages


def save_output(pages: List[Image.Image], out: Path) -> List[PageResult]:
    out.parent.mkdir(parents=True, exist_ok=True)
    results: List[PageResult] = []
    if out.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        # Write multiple files if multiple pages
        if len(pages) == 1:
            pages[0].save(out)
            results.append(
                PageResult(page_index=1, image_count=len(pages[0].getbands()), path=out)
            )
        else:
            for i, page in enumerate(pages, start=1):
                path_i = out.with_name(f"{out.stem}_{i}{out.suffix}")
                page.save(path_i)
                results.append(
                    PageResult(
                        page_index=i, image_count=len(page.getbands()), path=path_i
                    )
                )
        logger.info(f"Wrote {len(results)} image page(s) to {out.parent}")
        return results
    elif out.suffix.lower() == ".pdf":
        # Save as a single multipage PDF
        first, rest = pages[0], pages[1:]
        first.save(out, save_all=True, append_images=rest)
        results.append(PageResult(page_index=1, image_count=len(pages), path=out))
        logger.info(f"Wrote PDF with {len(pages)} page(s): {out}")
        return results
    else:
        raise ValueError("Output must be PNG/JPEG/PDF based on extension")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    root: Path = args.root
    if not root.exists() or not root.is_dir():
        logger.error("Root must be an existing directory")
        return 2

    images = [
        p
        for p in iter_image_files(root, args.recursive)
        if matches_filters(p, root, args.include, args.exclude)
    ]
    images.sort()
    if not images:
        logger.error("No matching images found")
        return 3

    tw, th = args.thumb
    layout = Layout(
        columns=args.cols,
        rows=args.rows,
        thumb_width=tw,
        thumb_height=th,
        spacing=args.spacing,
        margin=args.margin,
        label_height=args.label_height,
    )

    font = load_font(args.font, args.font_size)
    pages = build_pages(
        images, layout, bg=args.bg, draw_labels=bool(args.labels), font=font
    )
    save_output(pages, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
