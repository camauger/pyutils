"""Image deduper CLI using perceptual hashes (aHash/dHash/pHash/wHash).

Purpose
-------
Find exact and near-duplicate images in a directory tree using perceptual
hashing. Optionally generate a CSV/JSON report, move duplicates to a
quarantine folder, or delete them (with safety flags and dry-run).

Key features
------------
- Algorithms: aHash, dHash, pHash, wHash (via imagehash)
- Adjustable Hamming distance threshold for near-duplicates
- Include/exclude globs, recursive walking, follow symlinks
- Exact duplicate detection via cryptographic hash (SHA256)
- Group duplicates by a representative image; preserve first occurrence
- Actions: report (CSV/JSON), move --move-to, delete --delete (requires --yes)
- Dry-run support for safety; structured logging throughout

Dependencies
------------
- Pillow
- imagehash

Install extras (if using pyproject): pip install .[media]
Or directly: pip install Pillow imagehash

Usage examples
--------------
- Report near-duplicates (threshold=8) to CSV:
  python image_deduper.py ./photos --algo phash --threshold 8 --report dupes.csv --recursive

- Move near-duplicates to quarantine (dry-run first):
  python image_deduper.py ./photos --threshold 6 --move-to ./dupes --dry-run

- Delete exact duplicates only (no near-dup logic):
  python image_deduper.py ./photos --exact --delete --yes
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
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import imagehash  # type: ignore[import-not-found]
from PIL import Image

logger = logging.getLogger(__name__)


ALGO_MAP = {
    "ahash": imagehash.average_hash,
    "dhash": imagehash.dhash,
    "phash": imagehash.phash,
    "whash": imagehash.whash,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    sha256: str
    phash: Optional[imagehash.ImageHash]


@dataclass
class DuplicateGroup:
    representative: ImageInfo
    duplicates: List[ImageInfo]
    distance: int  # hamming distance used to group (for near-dup)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find exact and near-duplicate images via perceptual hashing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to image folder or a single file")

    sel = parser.add_argument_group("Selection")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )
    sel.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    sel.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks")

    algo = parser.add_argument_group("Hashing")
    algo.add_argument(
        "--algo",
        choices=sorted(ALGO_MAP.keys()),
        default="phash",
        help="Perceptual hashing algorithm",
    )
    algo.add_argument(
        "--threshold",
        type=int,
        default=8,
        help="Hamming distance threshold for near-duplicates",
    )
    algo.add_argument(
        "--exact", action="store_true", help="Only detect exact duplicates via SHA256"
    )

    act = parser.add_argument_group("Actions")
    act.add_argument("--report", type=Path, help="Write report CSV to this path")
    act.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Print JSON report to stdout",
    )
    act.add_argument(
        "--move-to",
        type=Path,
        help="Move duplicates to this folder (keeps one representative)",
    )
    act.add_argument(
        "--delete", action="store_true", help="Delete duplicates (requires --yes)"
    )
    act.add_argument(
        "--yes", action="store_true", help="Confirm destructive actions (delete/move)"
    )
    act.add_argument(
        "--dry-run", action="store_true", help="Do not change files; just report"
    )

    perf = parser.add_argument_group("Performance")
    perf.add_argument(
        "--max-files", type=int, help="Limit number of files for quick runs"
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def iter_image_files(
    root: Path, recursive: bool, follow_symlinks: bool
) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not recursive:
        for p in root.iterdir():
            if p.is_file():
                ext = p.suffix.lower()
                if ext in IMAGE_EXTS:
                    yield p
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_phash(path: Path, algo_name: str) -> Optional[imagehash.ImageHash]:
    try:
        with Image.open(path) as img:
            img.load()
            func = ALGO_MAP[algo_name]
            return func(img)
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"Failed to hash {path}: {ex}")
        return None


def collect_images(
    root: Path,
    include: List[str],
    exclude: List[str],
    recursive: bool,
    follow_symlinks: bool,
    algo_name: str,
    exact_only: bool,
    max_files: Optional[int],
) -> List[ImageInfo]:
    base = root.resolve()
    imgs: List[ImageInfo] = []
    for idx, p in enumerate(iter_image_files(base, recursive, follow_symlinks)):
        if not matches_filters(p, base, include, exclude):
            continue
        try:
            digest = sha256_file(p)
            ph = None if exact_only else compute_phash(p, algo_name)
            imgs.append(ImageInfo(path=p, sha256=digest, phash=ph))
        except Exception as ex:  # noqa: BLE001
            logger.warning(f"Skipping {p}: {ex}")
        if max_files is not None and len(imgs) >= max_files:
            break
    logger.info(f"Collected {len(imgs)} image(s)")
    return imgs


def group_exact_duplicates(images: List[ImageInfo]) -> List[DuplicateGroup]:
    by_digest: Dict[str, List[ImageInfo]] = {}
    for info in images:
        by_digest.setdefault(info.sha256, []).append(info)
    groups: List[DuplicateGroup] = []
    for digest, infos in by_digest.items():
        if len(infos) <= 1:
            continue
        rep = infos[0]
        dups = infos[1:]
        groups.append(DuplicateGroup(representative=rep, duplicates=dups, distance=0))
    return groups


def hamming_distance(h1: imagehash.ImageHash, h2: imagehash.ImageHash) -> int:
    return h1 - h2


def group_near_duplicates(
    images: List[ImageInfo], threshold: int
) -> List[DuplicateGroup]:
    # simple quadratic grouping; for large sets consider LSH / BK-Tree
    remaining = [img for img in images if img.phash is not None]
    groups: List[DuplicateGroup] = []
    used: set[Path] = set()
    for i, base in enumerate(remaining):
        if base.path in used:
            continue
        rep = base
        dup_list: List[ImageInfo] = []
        for j in range(i + 1, len(remaining)):
            cand = remaining[j]
            if cand.path in used or cand.phash is None or rep.phash is None:
                continue
            dist = hamming_distance(rep.phash, cand.phash)
            if dist <= threshold:
                dup_list.append(cand)
                used.add(cand.path)
        if dup_list:
            groups.append(
                DuplicateGroup(
                    representative=rep, duplicates=dup_list, distance=threshold
                )
            )
            used.add(rep.path)
    return groups


def write_report_csv(groups: List[DuplicateGroup], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["representative", "duplicate", "distance", "rep_sha256", "dup_sha256"]
        )
        for g in groups:
            for dup in g.duplicates:
                writer.writerow(
                    [
                        str(g.representative.path),
                        str(dup.path),
                        g.distance,
                        g.representative.sha256,
                        dup.sha256,
                    ]
                )


def write_report_json(groups: List[DuplicateGroup]) -> None:
    data = []
    for g in groups:
        data.append(
            {
                "representative": str(g.representative.path),
                "distance": g.distance,
                "rep_sha256": g.representative.sha256,
                "duplicates": [
                    {"path": str(d.path), "sha256": d.sha256} for d in g.duplicates
                ],
            }
        )
    print(json.dumps(data, ensure_ascii=False))


def act_on_duplicates(
    groups: List[DuplicateGroup],
    move_to: Optional[Path],
    delete: bool,
    yes: bool,
    dry_run: bool,
) -> None:
    if not groups:
        logger.info("No duplicate groups found.")
        return
    if delete and move_to is not None:
        raise ValueError("Choose either --delete or --move-to, not both")
    if (delete or move_to is not None) and not yes:
        logger.error("Destructive action requested without --yes. Aborting.")
        return

    if move_to is not None:
        move_to.mkdir(parents=True, exist_ok=True)

    total = 0
    for g in groups:
        for dup in g.duplicates:
            total += 1
            if dry_run:
                action = (
                    "MOVE" if move_to is not None else ("DELETE" if delete else "NONE")
                )
                logger.info(f"DRY-RUN {action}: {dup.path}")
                continue
            try:
                if move_to is not None:
                    target = move_to / dup.path.name
                    target = _resolve_collision(target)
                    shutil.move(str(dup.path), str(target))
                    logger.info(f"MOVED: {dup.path} -> {target}")
                elif delete:
                    dup.path.unlink()
                    logger.info(f"DELETED: {dup.path}")
            except Exception as ex:  # noqa: BLE001
                logger.error(f"Failed to act on {dup.path}: {ex}")
    logger.info(f"Processed {total} duplicate(s)")


def _resolve_collision(target: Path) -> Path:
    if not target.exists():
        return target
    stem, ext = target.stem, target.suffix
    counter = 1
    while True:
        cand = target.with_name(f"{stem}-{counter}{ext}")
        if not cand.exists():
            return cand
        counter += 1


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    base = args.path.resolve()

    images = collect_images(
        root=base,
        include=args.include,
        exclude=args.exclude,
        recursive=args.recursive,
        follow_symlinks=args.follow_symlinks,
        algo_name=args.algo,
        exact_only=args.exact,
        max_files=args.max_files,
    )

    groups: List[DuplicateGroup] = []

    # Exact duplicates
    exact_groups = group_exact_duplicates(images)
    if exact_groups:
        logger.info(f"Exact duplicate groups: {len(exact_groups)}")
        groups.extend(exact_groups)

    # Near duplicates (skip if exact only)
    if not args.exact:
        near_groups = group_near_duplicates(images, threshold=max(0, args.threshold))
        if near_groups:
            logger.info(
                f"Near-duplicate groups: {len(near_groups)} (threshold={args.threshold})"
            )
            groups.extend(near_groups)

    # Report
    if args.report:
        write_report_csv(groups, args.report)
        logger.info(f"Wrote CSV report: {args.report}")
    if args.json_out:
        write_report_json(groups)

    # Actions
    if args.move_to or args.delete:
        try:
            act_on_duplicates(
                groups,
                move_to=args.move_to,
                delete=args.delete,
                yes=args.yes,
                dry_run=args.dry_run,
            )
        except Exception as ex:  # noqa: BLE001
            logger.error(str(ex))
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
