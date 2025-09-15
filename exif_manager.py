"""EXIF manager CLI: inspect, export, strip, and edit image metadata.

Capabilities
------------
- List EXIF fields and export as JSON/CSV
- Strip all EXIF or remove only GPS data
- Set DateTimeOriginal from file mtime or a specific date
- Shift DateTimeOriginal by relative offsets (+/- days/hours/minutes)
- Batch over folders with include/exclude globs, recursive walking, dry-run

Dependencies
------------
- Pillow
- piexif

Install: pip install Pillow piexif

Examples
--------
- List EXIF to JSON recursively:
  python exif_manager.py ./photos --list --json --recursive

- Strip all EXIF (dry-run first):
  python exif_manager.py ./photos --strip --recursive --dry-run

- Remove GPS only:
  python exif_manager.py ./photos --remove-gps --include "*.jpg" --recursive

- Set date from file mtime:
  python exif_manager.py ./photos --set-date from-mtime --include "*.jpg"

- Shift date by +2h -30m:
  python exif_manager.py ./photos --shift-date "+2h,-30m" --include "*.jpg"
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, cast

import piexif  # type: ignore[import-not-found]
from PIL import Image

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".tif", ".tiff", ".webp"}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage EXIF metadata (list/strip/edit)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Folder or image file")

    sel = parser.add_argument_group("Selection")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )
    sel.add_argument("--recursive", action="store_true")

    ops = parser.add_argument_group("Operations")
    ops.add_argument("--list", action="store_true", help="List/export EXIF")
    ops.add_argument("--strip", action="store_true", help="Strip all EXIF data")
    ops.add_argument("--remove-gps", action="store_true", help="Remove GPS tags only")
    ops.add_argument(
        "--set-date",
        type=str,
        help="Set DateTimeOriginal: 'from-mtime' or ISO 'YYYY-MM-DD[ HH:MM:SS]'",
    )
    ops.add_argument(
        "--shift-date",
        type=str,
        help="Shift DateTimeOriginal by offsets like '+1d,-2h,+30m'",
    )

    out = parser.add_argument_group("Output")
    out.add_argument(
        "--json", dest="json_out", action="store_true", help="Print JSON for --list"
    )
    out.add_argument(
        "--csv", dest="csv_out", type=Path, help="Write CSV report for --list"
    )

    safety = parser.add_argument_group("Safety")
    safety.add_argument("--dry-run", action="store_true")
    safety.add_argument("--yes", action="store_true", help="Confirm write operations")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def iter_image_files(root: Path, recursive: bool) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not recursive:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p
        return
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for name in filenames:
            p = base / name
            if p.suffix.lower() in IMAGE_EXTS:
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


def load_exif_bytes(path: Path) -> Optional[bytes]:
    try:
        with Image.open(path) as img:
            img.load()
            return img.info.get("exif")
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"Failed to load EXIF from {path}: {ex}")
        return None


def exif_to_dict(exif_bytes: Optional[bytes]) -> Dict[str, Dict[str, str]]:
    if not exif_bytes:
        return {}
    try:
        exif = piexif.load(exif_bytes)
        out: Dict[str, Dict[str, str]] = {}
        for ifd_name in exif:
            if isinstance(exif[ifd_name], dict):
                out[ifd_name] = {}
                for tag, value in exif[ifd_name].items():
                    tag_name = piexif.TAGS[ifd_name].get(tag, {"name": str(tag)})[
                        "name"
                    ]
                    out[ifd_name][tag_name] = _format_exif_value(value)
        return out
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"Failed to parse EXIF: {ex}")
        return {}


def _format_exif_value(value: object) -> str:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return str(value)


def strip_exif(path: Path, dry_run: bool) -> bool:
    try:
        with Image.open(path) as img:
            img.load()
            pixels_iter = cast(Iterable, img.getdata())
            data = list(pixels_iter)
            mode = img.mode
            width, height = img.width, img.height
        if dry_run:
            logger.info(f"DRY-RUN STRIP: {path}")
            return True
        img2 = Image.new(mode, (width, height))
        img2.putdata(data)
        img2.save(path)
        return True
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to strip {path}: {ex}")
        return False


def remove_gps(exif: dict) -> dict:
    ifd = exif.get("GPS", {})
    if ifd:
        exif["GPS"] = {}
    return exif


def write_exif(path: Path, exif_dict: dict, dry_run: bool) -> bool:
    try:
        exif_bytes = piexif.dump(exif_dict)
        if dry_run:
            logger.info(f"DRY-RUN WRITE-EXIF: {path}")
            return True
        with Image.open(path) as img:
            img.save(path, exif=exif_bytes)
        return True
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to write EXIF for {path}: {ex}")
        return False


def parse_datetime(value: str) -> datetime:
    # Accept YYYY-MM-DD or YYYY-MM-DD HH:MM[:SS]
    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("Invalid datetime format. Use YYYY-MM-DD[ HH:MM[:SS]]")


def parse_shift(expr: str) -> timedelta:
    # e.g., "+1d,-2h,+30m"
    total = timedelta()
    if not expr:
        return total
    for token in expr.split(","):
        token = token.strip()
        if not token:
            continue
        sign = 1
        if token[0] in "+-":
            sign = 1 if token[0] == "+" else -1
            token = token[1:]
        if token.endswith("d"):
            total += sign * timedelta(days=int(token[:-1]))
        elif token.endswith("h"):
            total += sign * timedelta(hours=int(token[:-1]))
        elif token.endswith("m"):
            total += sign * timedelta(minutes=int(token[:-1]))
        elif token.endswith("s"):
            total += sign * timedelta(seconds=int(token[:-1]))
        else:
            raise ValueError(f"Invalid shift token: {token}")
    return total


def set_datetime_original(exif: dict, dt: datetime) -> dict:
    ts = dt.strftime("%Y:%m:%d %H:%M:%S")
    if "Exif" not in exif:
        exif["Exif"] = {}
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = ts
    return exif


def list_operation(paths: List[Path], json_out: bool, csv_out: Optional[Path]) -> None:
    rows: List[Dict[str, str]] = []
    for p in paths:
        exif_bytes = load_exif_bytes(p)
        exif = exif_to_dict(exif_bytes)
        rows.append({"path": str(p), **{"_has_exif": str(bool(exif))}})
    if json_out:
        print(json.dumps(rows, ensure_ascii=False))
    if csv_out:
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        with csv_out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=sorted({k for row in rows for k in row.keys()})
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        logger.info(f"Wrote CSV: {csv_out}")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    base = args.path.resolve()
    candidates = [
        p
        for p in iter_image_files(base, args.recursive)
        if matches_filters(p, base, args.include, args.exclude)
    ]
    if not candidates:
        logger.info("No matching images found.")
        return 0

    # Listing
    if args.list:
        list_operation(candidates, args.json_out, args.csv_out)
        # allow combining with other ops

    # Modifying operations require --yes unless dry-run
    wants_modify = args.strip or args.remove_gps or args.set_date or args.shift_date
    if wants_modify and not (args.dry_run or args.yes):
        logger.error("Modification requested without --yes or --dry-run. Aborting.")
        return 2

    for p in candidates:
        exif_bytes = load_exif_bytes(p)
        exif = (
            piexif.load(exif_bytes)
            if exif_bytes
            else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        )

        # Strip all EXIF
        if args.strip:
            strip_exif(p, args.dry_run)
            continue

        # Remove GPS
        if args.remove_gps and exif:
            exif = remove_gps(exif)

        # Set date
        if args.set_date:
            if args.set_date == "from-mtime":
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
                exif = set_datetime_original(exif, mtime)
            else:
                exif = set_datetime_original(exif, parse_datetime(args.set_date))

        # Shift date
        if args.shift_date:
            delta = parse_shift(args.shift_date)
            # Try to read existing DateTimeOriginal
            dto_raw = exif.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
            if dto_raw:
                try:
                    if isinstance(dto_raw, bytes):
                        dto_raw = dto_raw.decode("utf-8", errors="replace")
                    current = datetime.strptime(str(dto_raw), "%Y:%m:%d %H:%M:%S")
                except Exception:
                    current = datetime.fromtimestamp(p.stat().st_mtime)
            else:
                current = datetime.fromtimestamp(p.stat().st_mtime)
            exif = set_datetime_original(exif, current + delta)

        if args.remove_gps or args.set_date or args.shift_date:
            write_exif(p, exif, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
