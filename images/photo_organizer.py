"""Photo organizer CLI: sort images into date folders with rename & dedupe.

Features
--------
- Read date from EXIF DateTimeOriginal (fallback to file mtime)
- Organize into folder structures: yyyy/mm, yyyy/mm/dd, custom tokens
- Rename files using templates with tokens {yyyy},{mm},{dd},{HH},{MM},{SS},{orig},{hash}
- Copy or move files; dry-run support; JSON/CSV report of actions
- Dedupe by SHA256 (keep first) or by name; conflict resolution with suffixing
- Include/exclude globs; recursive traversal

Dependencies
------------
- Pillow
- piexif (optional, for EXIF dates)

Examples
--------
- Dry-run organize into yyyy/mm:
  python -m images.photo_organizer ./in ./photos --structure yyyy/mm --dry-run

- Use EXIF first, fallback to mtime; move and rename:
  python -m images.photo_organizer ./in ./photos --use exif,mtime --move \
    --name-template "{yyyy}-{mm}-{dd}_{HH}{MM}{SS}_{orig}"

- Dedupe by SHA256 and keep first, generating JSON report:
  python -m images.photo_organizer ./in ./photos --dedupe hash --json report.json
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from PIL import Image

try:
    import piexif  # type: ignore[import-not-found]
except Exception:
    piexif = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


@dataclass
class Plan:
    src: Path
    dest: Path
    action: str  # copy|move|skip
    reason: str
    hash: Optional[str]
    date: datetime


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize photos into date folders with rename & dedupe",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("src", type=Path, help="Source folder")
    parser.add_argument("dest", type=Path, help="Destination root folder")

    sel = parser.add_argument_group("Selection")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )
    sel.add_argument("--recursive", action="store_true")

    date = parser.add_argument_group("Date")
    date.add_argument(
        "--use",
        type=str,
        default="exif,mtime",
        help="Order to try for date: exif,mtime",
    )
    date.add_argument(
        "--structure",
        type=str,
        default="yyyy/mm/dd",
        help="Folder structure (tokens yyyy/mm/dd)",
    )

    name = parser.add_argument_group("Rename")
    name.add_argument(
        "--name-template", type=str, default="{orig}", help="Rename template"
    )

    act = parser.add_argument_group("Actions")
    act.add_argument(
        "--copy",
        action="store_true",
        help="Copy files (default if neither copy nor move)",
    )
    act.add_argument("--move", action="store_true", help="Move files instead of copy")
    act.add_argument("--dedupe", choices=["none", "hash", "name"], default="hash")
    act.add_argument("--dry-run", action="store_true")

    rep = parser.add_argument_group("Report")
    rep.add_argument("--json", type=Path, help="Write JSON report of planned actions")
    rep.add_argument("--csv", type=Path, help="Write CSV report of planned actions")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def iter_images(root: Path, recursive: bool) -> Iterator[Path]:
    if not root.exists():
        return
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


def matches(path: Path, base: Path, include: List[str], exclude: List[str]) -> bool:
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_exif_datetime(path: Path) -> Optional[datetime]:
    if piexif is None:
        return None
    try:
        with Image.open(path) as img:
            exif_bytes = img.info.get("exif")
        if not exif_bytes:
            return None
        exif = piexif.load(exif_bytes)
        raw = exif.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"No EXIF date for {path}: {ex}")
        return None


def get_photo_datetime(path: Path, order: List[str]) -> datetime:
    for source in order:
        if source == "exif":
            dt = read_exif_datetime(path)
            if dt:
                return dt
        if source == "mtime":
            return datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.fromtimestamp(path.stat().st_mtime)


def build_structure(dt: datetime, structure: string) -> str:  # type: ignore[name-defined]
    # tokens yyyy mm dd
    mapping = {
        "yyyy": dt.strftime("%Y"),
        "mm": dt.strftime("%m"),
        "dd": dt.strftime("%d"),
    }
    out = structure
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def build_name(dt: datetime, orig: str, hexdigest: str, template: str) -> str:
    tokens = {
        "yyyy": dt.strftime("%Y"),
        "mm": dt.strftime("%m"),
        "dd": dt.strftime("%d"),
        "HH": dt.strftime("%H"),
        "MM": dt.strftime("%M"),
        "SS": dt.strftime("%S"),
        "orig": orig,
        "hash": hexdigest[:12],
    }
    name = template
    for k, v in tokens.items():
        name = name.replace("{" + k + "}", v)
    return name


def plan_actions(
    src: Path,
    dest: Path,
    include: List[str],
    exclude: List[str],
    recursive: bool,
    order: List[str],
    structure: str,
    template: str,
    move: bool,
    dedupe: str,
) -> List[Plan]:
    plans: List[Plan] = []
    seen_hash: Dict[str, Path] = {}
    base = src.resolve()
    for p in iter_images(base, recursive):
        if not matches(p, base, include, exclude):
            continue
        dt = get_photo_datetime(p, order)
        hexdigest = sha256_file(p)
        if dedupe == "hash" and hexdigest in seen_hash:
            plans.append(
                Plan(
                    src=p,
                    dest=seen_hash[hexdigest],
                    action="skip",
                    reason="duplicate-hash",
                    hash=hexdigest,
                    date=dt,
                )
            )
            continue
        seen_hash.setdefault(hexdigest, p)
        folder = build_structure(dt, structure)
        out_dir = dest / folder
        out_name = build_name(dt, p.stem, hexdigest, template) + p.suffix.lower()
        out_path = out_dir / out_name
        action = "move" if move else "copy"
        plans.append(
            Plan(
                src=p,
                dest=out_path,
                action=action,
                reason="ok",
                hash=hexdigest,
                date=dt,
            )
        )
    return plans


def resolve_collision(path: Path) -> Path:
    if not path.exists():
        return path
    stem, ext = path.stem, path.suffix
    counter = 1
    while True:
        cand = path.with_name(f"{stem}-{counter}{ext}")
        if not cand.exists():
            return cand
        counter += 1


def execute_plans(plans: List[Plan], dry_run: bool) -> Tuple[int, int]:
    copied = 0
    moved = 0
    for pl in plans:
        if pl.action == "skip":
            logger.info(f"SKIP duplicate: {pl.src}")
            continue
        target = resolve_collision(pl.dest)
        if dry_run:
            logger.info(f"DRY-RUN {pl.action.upper()}: {pl.src} -> {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if pl.action == "move":
                shutil.move(str(pl.src), str(target))
                moved += 1
            else:
                shutil.copy2(str(pl.src), str(target))
                copied += 1
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed {pl.action} {pl.src} -> {target}: {ex}")
    return copied, moved


def write_reports(
    plans: List[Plan], json_path: Optional[Path], csv_path: Optional[Path]
) -> None:
    rows = [
        {
            "src": str(p.src),
            "dest": str(p.dest),
            "action": p.action,
            "reason": p.reason,
            "hash": p.hash or "",
            "date": p.date.isoformat(),
        }
        for p in plans
    ]
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Wrote JSON: {json_path}")
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Wrote CSV: {csv_path}")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    order = [t.strip() for t in args.use.split(",") if t.strip()]
    if not order:
        order = ["exif", "mtime"]

    plans = plan_actions(
        src=args.src,
        dest=args.dest,
        include=args.include,
        exclude=args.exclude,
        recursive=args.recursive,
        order=order,
        structure=args.structure,
        template=args.name_template,
        move=args.move,
        dedupe=args.dedupe,
    )

    if args.json or args.csv:
        write_reports(plans, args.json, args.csv)

    copied, moved = execute_plans(plans, args.dry_run)
    logger.info(f"Done. planned={len(plans)} copied={copied} moved={moved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
