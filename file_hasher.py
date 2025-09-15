"""File hasher CLI: generate and verify checksum manifests.

Features:
- Recursively hash files (SHA256 by default; supports sha512, sha1, md5)
- Include/exclude globs; follow or ignore symlinks
- Output to manifest file (text or JSON) or stdout
- Verify mode reads manifest and checks current files
- Optional parallel hashing
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import fnmatch
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)


SUPPORTED_ALGOS = {"sha256", "sha512", "sha1", "md5"}


@dataclass(frozen=True)
class HashRecord:
    path: str  # stored path (relative or absolute depending on options)
    algo: str
    digest: str


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute and verify file checksums.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="Path to file or directory")

    sel = parser.add_argument_group("Selection")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob to include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob to exclude (repeatable)"
    )
    sel.add_argument(
        "--recursive", action="store_true", help="Recurse into directories"
    )
    sel.add_argument(
        "--follow-symlinks", action="store_true", help="Follow symlinks while walking"
    )

    out = parser.add_argument_group("Output")
    out.add_argument("--algo", choices=sorted(SUPPORTED_ALGOS), default="sha256")
    out.add_argument("--manifest", type=Path, help="Write manifest to this file (text)")
    out.add_argument(
        "--json",
        dest="json_out",
        action="store_true",
        help="Output JSON manifest to stdout",
    )
    out.add_argument(
        "--relative-paths", action="store_true", help="Store relative paths in manifest"
    )

    ver = parser.add_argument_group("Verify")
    ver.add_argument(
        "--verify",
        type=Path,
        help="Verify against an existing manifest file (text or JSON)",
    )

    perf = parser.add_argument_group("Performance")
    perf.add_argument("--parallel", action="store_true", help="Hash files in parallel")
    perf.add_argument(
        "--workers", type=int, default=os.cpu_count() or 4, help="Max worker threads"
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def iter_files(root: Path, recursive: bool, follow_symlinks: bool) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not recursive:
        for p in root.iterdir():
            if p.is_file() or (follow_symlinks and p.is_symlink() and p.exists()):
                yield p
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        base = Path(dirpath)
        for name in filenames:
            yield base / name


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


def hash_file(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_record(path: Path, base: Path, algo: str, relative_paths: bool) -> HashRecord:
    stored = str(path.relative_to(base)) if relative_paths else str(path.resolve())
    digest = hash_file(path, algo)
    return HashRecord(path=stored, algo=algo, digest=digest)


def generate_manifest(
    root: Path,
    algo: str,
    include: List[str],
    exclude: List[str],
    recursive: bool,
    follow_symlinks: bool,
    relative_paths: bool,
    do_parallel: bool,
    workers: int,
) -> List[HashRecord]:
    base = root.resolve()
    files = [
        p
        for p in iter_files(base, recursive, follow_symlinks)
        if matches_filters(p, base, include, exclude)
    ]
    files.sort()
    logger.info(f"Found {len(files)} file(s) to hash")

    if not do_parallel or not files:
        return [make_record(p, base, algo, relative_paths) for p in files]

    results: List[HashRecord] = []

    def _task(p: Path) -> HashRecord:
        return make_record(p, base, algo, relative_paths)

    with futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for rec in ex.map(_task, files, chunksize=8):
            results.append(rec)
    return results


def write_manifest_text(records: List[HashRecord], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(f"{r.algo}  {r.digest}  {r.path}\n")


def write_manifest_json(records: List[HashRecord]) -> None:
    data = [r.__dict__ for r in records]
    print(json.dumps(data, ensure_ascii=False))


def read_manifest(path: Path) -> List[HashRecord]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        out: List[HashRecord] = []
        for item in data:
            out.append(
                HashRecord(
                    path=str(item["path"]),
                    algo=str(item["algo"]),
                    digest=str(item["digest"]),
                )
            )
        return out
    except Exception:
        # parse simple text format: algo  digest  path
        records: List[HashRecord] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                algo, digest, stored_path = line.split(maxsplit=2)
                records.append(HashRecord(path=stored_path, algo=algo, digest=digest))
            except Exception:
                raise ValueError(f"Invalid manifest line: {line}")
        return records


def verify_manifest(records: List[HashRecord], base: Path) -> Tuple[int, int, int]:
    ok = 0
    missing = 0
    mismatched = 0
    for r in records:
        p = (base / r.path) if not Path(r.path).is_absolute() else Path(r.path)
        if not p.exists() or not p.is_file():
            logger.error(f"MISSING: {r.path}")
            missing += 1
            continue
        actual = hash_file(p, r.algo)
        if actual == r.digest:
            ok += 1
        else:
            logger.error(
                f"MISMATCH: {r.path}\n  expected: {r.digest}\n  actual:   {actual}"
            )
            mismatched += 1
    return ok, missing, mismatched


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    base = args.path.resolve()

    if args.verify:
        try:
            records = read_manifest(args.verify)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to read manifest: {ex}")
            return 2
        ok, missing, mismatched = verify_manifest(records, base)
        total = len(records)
        logger.info(
            f"Verified {ok}/{total} OK; missing={missing}, mismatched={mismatched}"
        )
        return 0 if (missing == 0 and mismatched == 0) else 1

    # generate mode
    records = generate_manifest(
        root=base,
        algo=args.algo,
        include=args.include,
        exclude=args.exclude,
        recursive=args.recursive,
        follow_symlinks=args.follow_symlinks,
        relative_paths=args.relative_paths,
        do_parallel=args.parallel,
        workers=args.workers,
    )

    if args.manifest:
        write_manifest_text(records, args.manifest)
        logger.info(f"Wrote manifest: {args.manifest}")
    elif args.json_out:
        write_manifest_json(records)
    else:
        # default to text on stdout
        for r in records:
            print(f"{r.algo}  {r.digest}  {r.path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
