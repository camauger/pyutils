"""HEIC/HEIF converter CLI: convert to JPEG/PNG/WebP with options.

Dependencies:
- pillow-heif (registers HEIF opener for Pillow)
- Pillow

Examples:
- Convert all HEIC to JPEG @ quality 90, preserve EXIF, auto-orient:
  python -m images.image_heic_converter ./in ./out --to jpeg --quality 90 --preserve-exif --recursive

- Convert to WebP with max size 2048x2048 and strip metadata:
  python -m images.image_heic_converter ./in ./out --to webp --max-width 2048 --max-height 2048 --strip-exif --recursive

- Only convert matching pattern, keep structure:
  python -m images.image_heic_converter ./in ./out --to png --include "*.HEIC" --recursive
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, cast

# Register HEIF with Pillow
try:
    import pillow_heif  # type: ignore[import-not-found]

    pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pillow_heif = None  # type: ignore[assignment]

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

IN_EXTS = {".heic", ".heif", ".HEIC", ".HEIF"}
OUT_FORMATS = {"jpeg", "png", "webp"}


@dataclass
class ConvertPlan:
    src: Path
    dest: Path
    format: str


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert HEIC/HEIF images to JPEG/PNG/WebP.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("src", type=Path, help="Source file or directory")
    parser.add_argument("dest", type=Path, help="Destination file or directory root")

    sel = parser.add_argument_group("Selection")
    sel.add_argument("--recursive", action="store_true")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )

    out = parser.add_argument_group("Output")
    out.add_argument(
        "--to", choices=sorted(OUT_FORMATS), default="jpeg", help="Output format"
    )
    out.add_argument(
        "--quality", type=int, default=90, help="JPEG/WebP quality (1-100)"
    )
    out.add_argument(
        "--lossless", action="store_true", help="Lossless WebP when --to webp"
    )
    out.add_argument("--max-width", type=int, help="Resize to max width (px)")
    out.add_argument("--max-height", type=int, help="Resize to max height (px)")
    out.add_argument(
        "--keep-structure",
        action="store_true",
        help="Preserve directory structure under dest when src is a folder",
    )

    meta = parser.add_argument_group("Metadata")
    meta.add_argument(
        "--preserve-exif", action="store_true", help="Attempt to preserve EXIF"
    )
    meta.add_argument("--strip-exif", action="store_true", help="Strip EXIF metadata")
    meta.add_argument(
        "--auto-orient", action="store_true", help="Apply EXIF orientation"
    )

    safety = parser.add_argument_group("Safety")
    safety.add_argument("--dry-run", action="store_true")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def iter_heic_files(root: Path, recursive: bool) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not recursive:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in {".heic", ".heif"}:
                yield p
        return
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for name in filenames:
            p = base / name
            if p.suffix.lower() in {".heic", ".heif"}:
                yield p


def matches_filters(
    path: Path, base: Path, include: List[str], exclude: List[str]
) -> bool:
    rel = str(path.relative_to(base))
    name = path.name
    if include:
        ok = any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in include
        )
        if not ok:
            return False
    if exclude:
        if any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in exclude
        ):
            return False
    return True


def compute_dest_path(
    src: Path, src_root: Path, dest_root: Path, keep_structure: bool, out_format: str
) -> Path:
    if keep_structure:
        rel = src.relative_to(src_root)
        rel_no_ext = rel.with_suffix("")
        return dest_root / rel_no_ext.with_suffix(f".{out_format}")
    # flat: mirror filename only
    return (dest_root / src.name).with_suffix(f".{out_format}")


def resize_to_bounds(
    img: Image.Image, max_w: Optional[int], max_h: Optional[int]
) -> Image.Image:
    if max_w is None and max_h is None:
        return img
    w, h = img.width, img.height
    tw = max_w if max_w is not None else w
    th = max_h if max_h is not None else h
    scale = min(tw / w, th / h)
    if scale >= 1.0:
        return img
    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore[attr-defined]
    return img.resize(
        (max(1, int(w * scale)), max(1, int(h * scale))), resample=resample
    )


def convert_one(
    src: Path,
    dest: Path,
    out_format: str,
    quality: int,
    lossless_webp: bool,
    preserve_exif: bool,
    strip_exif: bool,
    auto_orient: bool,
    max_w: Optional[int],
    max_h: Optional[int],
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info(f"DRY-RUN CONVERT: {src} -> {dest} ({out_format})")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        if auto_orient:
            im = cast(Image.Image, ImageOps.exif_transpose(im) or im)
        im = resize_to_bounds(cast(Image.Image, im), max_w, max_h)
        save_kwargs: dict[str, object] = {}
        fmt = out_format.upper()
        if fmt in {"JPEG", "WEBP"}:
            save_kwargs["quality"] = max(1, min(100, quality))
        if fmt == "WEBP" and lossless_webp:
            save_kwargs["lossless"] = True
        if fmt == "JPEG":
            save_kwargs["optimize"] = True
        if preserve_exif and not strip_exif:
            exif_bytes = im.info.get("exif")
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
        # When strip_exif is set, we do not pass exif back
        im.convert("RGB").save(dest, format=fmt, **save_kwargs)


def plan_conversions(
    src: Path,
    dest: Path,
    include: List[str],
    exclude: List[str],
    recursive: bool,
    keep_structure: bool,
    out_format: str,
) -> List[ConvertPlan]:
    base = src.resolve()
    files = [
        p
        for p in iter_heic_files(base, recursive)
        if matches_filters(p, base, include, exclude)
    ]
    plans: List[ConvertPlan] = []
    for f in files:
        out_path = (
            dest
            if dest.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            else compute_dest_path(f, base, dest, keep_structure, out_format)
        )
        if out_path.is_dir():
            out_path = compute_dest_path(f, base, out_path, keep_structure, out_format)
        plans.append(ConvertPlan(src=f, dest=out_path, format=out_format))
    return plans


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    if pillow_heif is None:
        logger.error("pillow-heif is not installed. Run: pip install pillow-heif")
        return 2

    if args.to not in OUT_FORMATS:
        logger.error("Unsupported output format")
        return 2

    plans = plan_conversions(
        src=args.src,
        dest=args.dest,
        include=args.include,
        exclude=args.exclude,
        recursive=args.recursive,
        keep_structure=args.keep_structure,
        out_format=args.to,
    )

    if not plans:
        logger.info("No matching HEIC/HEIF files found.")
        return 0

    for pl in plans:
        try:
            convert_one(
                src=pl.src,
                dest=pl.dest,
                out_format=pl.format,
                quality=args.quality,
                lossless_webp=args.lossless,
                preserve_exif=args.preserve_exif,
                strip_exif=args.strip_exif,
                auto_orient=args.auto_orient,
                max_w=args.max_width,
                max_h=args.max_height,
                dry_run=args.dry_run,
            )
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to convert {pl.src}: {ex}")

    logger.info(f"Processed {len(plans)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
