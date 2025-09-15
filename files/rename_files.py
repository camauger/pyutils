#!/usr/bin/env python3
"""
rename_files.py

A flexible CLI tool to batch-rename files in a directory.

Features:
- Prefix/suffix
- Find/replace and regex substitutions
- Case transforms (lower/upper/title)
- Enumeration with padding and sorting
- Custom templates with tokens: {n}, {stem}, {ext}, {parent}
- Include/exclude globs, extension filters, recursive mode
- Dry-run preview
- Collision handling: skip, overwrite, number, error

Examples:
  - Preview adding a prefix to all .jpg files:
    python rename_files.py ./photos --include "*.jpg" --prefix "vacation_" --dry-run

  - Replace spaces with underscores, recursively:
    python rename_files.py . --recursive --find " " --replace-with "_"

  - Regex rename: remove digits at end of stem:
    python rename_files.py . --regex "(.*?)(\\d+)$" --regex-repl "\\1" --dry-run

  - Enumerate with padding and template:
    python rename_files.py ./docs --include "*.pdf" --enumerate --pad 3 --template "{n}_{stem}{ext}"

  - Change extension and lowercase names:
    python rename_files.py ./audio --include "*.WAV" --lower --new-ext .wav

Notes:
- On Windows, invalid filename characters are sanitized by default.

Rename to a fixed base name with numbering
Use --enumerate with a --template:
Keep original extensions:
Drop extensions:
Force a specific extension (e.g., .jpg):
Notes:
{n} is the counter; --start sets the first number; --pad controls zero-padding (use 1 for no leading zeros).
Add --recursive if files are in subfolders.
Use --sort mtime to number by modified time instead of name.


"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')


@dataclass
class RenamePlan:
    source_path: Path
    target_path: Path
    preview_old: str
    preview_new: str


def parse_arguments() -> argparse.Namespace:
    """Build and parse CLI arguments for the renaming tool."""
    parser = argparse.ArgumentParser(
        description="Batch rename files in a directory with rich options.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to operate on",
    )

    # Selection options
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="Only include files matching this glob (can be repeated)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Exclude files matching this glob (can be repeated)",
    )
    parser.add_argument(
        "--ext-filter",
        nargs="*",
        default=[],
        metavar=".ext",
        help="Only include files with these extensions (case-insensitive)",
    )

    # Transform options
    parser.add_argument("--prefix", default="", help="Prefix to add to stem")
    parser.add_argument("--suffix", default="", help="Suffix to add to stem")
    parser.add_argument("--find", default=None, help="Find this substring in stem")
    parser.add_argument(
        "--replace-with",
        default="",
        help="Replace matches of --find with this string (default empty)",
    )
    parser.add_argument("--regex", default=None, help="Regex pattern applied to stem")
    parser.add_argument(
        "--regex-repl",
        default="",
        help="Replacement for --regex (supports backrefs like \\1)",
    )
    case_group = parser.add_mutually_exclusive_group()
    case_group.add_argument("--lower", action="store_true", help="Lowercase stem")
    case_group.add_argument("--upper", action="store_true", help="Uppercase stem")
    case_group.add_argument("--title", action="store_true", help="Title-case stem")
    parser.add_argument(
        "--new-ext",
        default=None,
        help="Change extension to this (e.g., .txt). If omitted, keep original",
    )
    parser.add_argument(
        "--template",
        default=None,
        help=(
            "Custom filename template. Tokens: {n} (enum), {stem}, {ext}, {parent}. "
            "If provided, it overrides prefix/suffix/case for final composition."
        ),
    )

    # Enumeration and ordering
    parser.add_argument(
        "--enumerate",
        action="store_true",
        help="Add an incrementing number {n} starting at --start",
    )
    parser.add_argument("--start", type=int, default=1, help="Start index for {n}")
    parser.add_argument(
        "--pad",
        type=int,
        default=2,
        help="Zero-padding width for {n} (e.g., 2 -> 01, 3 -> 001)",
    )
    parser.add_argument(
        "--sort",
        choices=["name", "mtime"],
        default="name",
        help="Sort files before enumeration",
    )

    # Behavior
    parser.add_argument(
        "--on-collision",
        choices=["skip", "overwrite", "number", "error"],
        default="number",
        help="What to do if target exists",
    )
    parser.add_argument(
        "--sanitize",
        action="store_true",
        default=True,
        help="Sanitize invalid filename characters on Windows",
    )
    parser.add_argument(
        "--no-sanitize",
        dest="sanitize",
        action="store_false",
        help="Do not sanitize invalid characters",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without renaming",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def iter_files(base_dir: Path, recursive: bool) -> Iterable[Path]:
    """Yield files under `base_dir`. Recurse if `recursive` is True."""
    if recursive:
        yield from (p for p in base_dir.rglob("*") if p.is_file())
    else:
        yield from (p for p in base_dir.glob("*") if p.is_file())


def matches_filters(
    path: Path,
    base_dir: Path,
    include_globs: List[str],
    exclude_globs: List[str],
    ext_filter: List[str],
) -> bool:
    """Return True if `path` matches include/exclude and extension filters."""
    rel = str(path.relative_to(base_dir))
    name = path.name

    # Extension filter
    if ext_filter:
        lowercase_exts = {
            e.lower() if e.startswith(".") else f".{e.lower()}" for e in ext_filter
        }
        if path.suffix.lower() not in lowercase_exts:
            return False

    # Include
    if include_globs:
        if not any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g)
            for g in include_globs
        ):
            return False

    # Exclude
    if exclude_globs:
        if any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g)
            for g in exclude_globs
        ):
            return False

    return True


def sanitize_filename(name: str) -> str:
    """Sanitize a filename for Windows by replacing invalid characters with underscores."""
    if os.name == "nt":
        return "".join((ch if ch not in WINDOWS_INVALID_CHARS else "_") for ch in name)
    return name


def build_new_name(
    path: Path,
    stem_transform: str,
    ext: str,
    template: Optional[str],
    seq_num: Optional[int],
    pad: int,
) -> str:
    """Compose a new filename based on a template or transformed stem and extension."""
    parent_name = path.parent.name
    if template is not None:
        n_token = f"{seq_num:0{pad}d}" if seq_num is not None else ""
        composed = template.format(
            n=n_token, stem=stem_transform, ext=ext, parent=parent_name
        )
        return composed
    else:
        if seq_num is not None:
            n_token = f"{seq_num:0{pad}d}"
            return f"{n_token}_{stem_transform}{ext}"
        return f"{stem_transform}{ext}"


def apply_transformations(
    stem: str,
    prefix: str,
    suffix: str,
    find: Optional[str],
    replace_with: str,
    regex: Optional[str],
    regex_repl: str,
    lower: bool,
    upper: bool,
    title: bool,
) -> str:
    """Apply prefix/suffix, find/replace, regex, and case transforms to a stem."""
    transformed = stem
    if find is not None:
        transformed = transformed.replace(find, replace_with)
    if regex is not None:
        try:
            pattern = re.compile(regex)
            transformed = pattern.sub(regex_repl, transformed)
        except re.error as ex:
            raise ValueError(f"Invalid regex '{regex}': {ex}") from ex
    if lower:
        transformed = transformed.lower()
    elif upper:
        transformed = transformed.upper()
    elif title:
        transformed = transformed.title()
    transformed = f"{prefix}{transformed}{suffix}"
    return transformed


def resolve_collision(target: Path, strategy: str) -> Path:
    """Resolve a filename collision by applying the selected strategy."""
    if not target.exists():
        return target
    if strategy == "skip":
        return target
    if strategy == "overwrite":
        return target
    if strategy == "error":
        return target
    # strategy == "number": append -1, -2, ... before extension
    stem, ext = target.stem, target.suffix
    counter = 1
    while True:
        candidate = target.with_name(f"{stem}-{counter}{ext}")
        if not candidate.exists():
            return candidate
        counter += 1


def plan_operations(args: argparse.Namespace) -> Tuple[List[RenamePlan], List[str]]:
    """Create a list of rename plans and warnings based on CLI `args`."""
    base_dir = Path(args.path).resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        raise SystemExit(f"Path is not a directory: {base_dir}")

    files = [
        p
        for p in iter_files(base_dir, args.recursive)
        if matches_filters(p, base_dir, args.include, args.exclude, args.ext_filter)
    ]

    if args.sort == "mtime":
        files.sort(key=lambda p: (p.stat().st_mtime, p.name))
    else:
        files.sort(key=lambda p: p.name)

    plans: List[RenamePlan] = []
    warnings: List[str] = []

    seq = (
        args.start
        if (args.enumerate or (args.template and "{n}" in args.template))
        else None
    )

    for p in files:
        orig_stem = p.stem
        orig_ext = p.suffix
        new_ext = args.new_ext if args.new_ext is not None else orig_ext
        if new_ext and not new_ext.startswith("."):
            new_ext = "." + new_ext

        stem_tx = apply_transformations(
            stem=orig_stem,
            prefix=args.prefix,
            suffix=args.suffix,
            find=args.find,
            replace_with=args.replace_with,
            regex=args.regex,
            regex_repl=args.regex_repl,
            lower=args.lower,
            upper=args.upper,
            title=args.title,
        )

        n_value = seq if seq is not None else None
        new_name = build_new_name(
            path=p,
            stem_transform=stem_tx,
            ext=new_ext,
            template=args.template,
            seq_num=n_value,
            pad=args.pad,
        )

        if args.sanitize:
            new_name = sanitize_filename(new_name)

        if new_name == p.name:
            # No change
            if seq is not None:
                seq += 1
            continue

        target = p.with_name(new_name)

        if target.exists():
            if args.on_collision == "skip":
                warnings.append(f"Skipping (exists): {p.name} -> {new_name}")
                if seq is not None:
                    seq += 1
                continue
            elif args.on_collision == "overwrite":
                pass  # allowed, will unlink later
            elif args.on_collision == "error":
                warnings.append(f"Collision error (exists): {p.name} -> {new_name}")
                if seq is not None:
                    seq += 1
                continue
            elif args.on_collision == "number":
                target = resolve_collision(target, "number")

        plans.append(
            RenamePlan(
                source_path=p,
                target_path=target,
                preview_old=p.name,
                preview_new=target.name,
            )
        )

        if seq is not None:
            seq += 1

    return plans, warnings


def execute_plans(
    plans: List[RenamePlan], dry_run: bool, on_collision: str
) -> Tuple[int, int, int]:
    """Execute planned renames. Returns (changed, skipped, failed)."""
    changed = 0
    skipped = 0
    failed = 0

    for plan in plans:
        src = plan.source_path
        dst = plan.target_path
        if dry_run:
            logger.info(f"DRY-RUN: {plan.preview_old} -> {plan.preview_new}")
            skipped += 1
            continue

        try:
            if dst.exists() and on_collision == "overwrite":
                # Only unlink files, not directories (we only target files anyway)
                dst.unlink()
            src.rename(dst)
            logger.info(f"RENAMED: {plan.preview_old} -> {plan.preview_new}")
            changed += 1
        except Exception as ex:  # noqa: BLE001
            logger.error(f"ERROR: {src.name} -> {dst.name}: {ex}")
            failed += 1

    return changed, skipped, failed


def main() -> int:
    """CLI entrypoint."""
    args = parse_arguments()

    # Configure logging to stdout for CLI friendliness
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )
    global logger  # ensure module-level logger binds to configured handlers
    logger = logging.getLogger(__name__)

    try:
        plans, warnings = plan_operations(args)
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to plan operations: {ex}")
        return 2

    for w in warnings:
        logger.warning(w)

    if not plans:
        logger.info("No files to rename or no changes detected.")
        return 0

    changed, skipped, failed = execute_plans(plans, args.dry_run, args.on_collision)

    logger.info(
        f"\nSummary: planned={len(plans)}, renamed={changed}, previewed/skipped={skipped}, errors={failed}"
    )

    return 0 if (failed == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
