"""Duplicate file finder CLI - Find duplicate files by content hash.

Features:
- Hash-based duplicate detection (SHA256)
- Size-based pre-filtering for efficiency
- Interactive selection mode
- Move/delete/hardlink duplicates
- JSON report generation
- Dry-run mode
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a file."""

    path: Path
    size: int
    hash: str | None = None


def hash_file(path: Path, algo: str = "sha256") -> str:
    """Compute hash of file.

    Args:
        path: Path to file
        algo: Hash algorithm to use

    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_duplicates(
    root: Path,
    recursive: bool = True,
    min_size: int = 0,
) -> Dict[str, List[FileInfo]]:
    """Find duplicate files in directory.

    Args:
        root: Root directory to search
        recursive: Recurse into subdirectories
        min_size: Minimum file size to consider

    Returns:
        Dict mapping hash to list of FileInfo objects
    """
    # First pass: group by size
    size_groups: Dict[int, List[Path]] = defaultdict(list)

    pattern = "**/*" if recursive else "*"
    for path in root.glob(pattern):
        if path.is_file():
            try:
                size = path.stat().st_size
                if size >= min_size:
                    size_groups[size].append(path)
            except (PermissionError, FileNotFoundError) as e:
                logger.warning(f"Skipping {path}: {e}")

    # Second pass: hash files with duplicate sizes
    hash_groups: Dict[str, List[FileInfo]] = defaultdict(list)

    for size, paths in size_groups.items():
        if len(paths) < 2:
            continue

        logger.info(f"Hashing {len(paths)} files of size {size}")
        for path in paths:
            try:
                file_hash = hash_file(path)
                hash_groups[file_hash].append(FileInfo(path=path, size=size, hash=file_hash))
            except (PermissionError, IOError) as e:
                logger.warning(f"Cannot hash {path}: {e}")

    # Filter to only actual duplicates
    return {h: files for h, files in hash_groups.items() if len(files) > 1}


def interactive_select(duplicates: Dict[str, List[FileInfo]]) -> List[Path]:
    """Interactively select which files to keep.

    Args:
        duplicates: Dict of hash to file list

    Returns:
        List of files to delete
    """
    to_delete: List[Path] = []

    for file_hash, files in duplicates.items():
        print(f"\n=== Duplicate group ({len(files)} files, hash: {file_hash[:8]}...) ===")
        for i, file in enumerate(files, 1):
            print(f"  [{i}] {file.path} ({file.size} bytes)")

        while True:
            choice = input(f"Keep which file? (1-{len(files)}, 'a' for all, 's' to skip): ").strip().lower()
            if choice == "s":
                break
            if choice == "a":
                continue
            try:
                keep_idx = int(choice) - 1
                if 0 <= keep_idx < len(files):
                    for i, f in enumerate(files):
                        if i != keep_idx:
                            to_delete.append(f.path)
                    break
            except ValueError:
                pass
            print("Invalid choice")

    return to_delete


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find and handle duplicate files by content hash",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("path", type=Path, help="Directory to scan")
    parser.add_argument("--recursive", action="store_true", default=True, help="Scan recursively")
    parser.add_argument("--no-recursive", dest="recursive", action="store_false", help="Don't scan recursively")
    parser.add_argument("--min-size", type=int, default=0, help="Minimum file size in bytes")

    parser.add_argument(
        "--action",
        choices=["delete", "move", "hardlink", "report"],
        default="report",
        help="Action to take on duplicates",
    )
    parser.add_argument("--keep", choices=["first", "last", "newest", "oldest"], default="first", help="Which file to keep")
    parser.add_argument("--move-to", type=Path, help="Directory to move duplicates to")
    parser.add_argument("--interactive", action="store_true", help="Interactively select files to keep")

    parser.add_argument("--json", dest="json_output", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", type=Path, help="Write report to file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def select_files_to_delete(files: List[FileInfo], keep_strategy: str) -> List[Path]:
    """Select which files to delete based on strategy.

    Args:
        files: List of duplicate files
        keep_strategy: Which file to keep

    Returns:
        List of paths to delete
    """
    if len(files) <= 1:
        return []

    if keep_strategy == "first":
        keep_idx = 0
    elif keep_strategy == "last":
        keep_idx = len(files) - 1
    elif keep_strategy == "newest":
        keep_idx = max(range(len(files)), key=lambda i: files[i].path.stat().st_mtime)
    elif keep_strategy == "oldest":
        keep_idx = min(range(len(files)), key=lambda i: files[i].path.stat().st_mtime)
    else:
        keep_idx = 0

    return [f.path for i, f in enumerate(files) if i != keep_idx]


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s: %(message)s",
    )

    if not args.path.is_dir():
        logger.error(f"Not a directory: {args.path}")
        return 1

    logger.info(f"Scanning {args.path} for duplicates...")
    duplicates = find_duplicates(args.path, args.recursive, args.min_size)

    if not duplicates:
        logger.info("No duplicates found")
        return 0

    total_files = sum(len(files) for files in duplicates.values())
    total_wasted = sum(files[0].size * (len(files) - 1) for files in duplicates.values())

    logger.info(f"Found {len(duplicates)} duplicate groups ({total_files} files)")
    logger.info(f"Potential space savings: {total_wasted:,} bytes")

    # Generate report
    if args.json_output or args.output:
        report = {
            "groups": len(duplicates),
            "total_files": total_files,
            "wasted_space": total_wasted,
            "duplicates": [
                {
                    "hash": file_hash,
                    "size": files[0].size,
                    "count": len(files),
                    "files": [str(f.path) for f in files],
                }
                for file_hash, files in duplicates.items()
            ],
        }

        report_json = json.dumps(report, indent=2)
        if args.output:
            args.output.write_text(report_json)
            logger.info(f"Report written to {args.output}")
        else:
            print(report_json)

        if args.action == "report":
            return 0

    # Handle duplicates
    if args.interactive:
        to_delete = interactive_select(duplicates)
    else:
        to_delete = []
        for files in duplicates.values():
            to_delete.extend(select_files_to_delete(files, args.keep))

    if not to_delete:
        logger.info("No files selected for action")
        return 0

    logger.info(f"Will {args.action} {len(to_delete)} files")

    if args.dry_run:
        for path in to_delete:
            logger.info(f"Would {args.action}: {path}")
        return 0

    # Perform action
    for path in to_delete:
        try:
            if args.action == "delete":
                path.unlink()
                logger.info(f"Deleted: {path}")
            elif args.action == "move":
                if not args.move_to:
                    logger.error("--move-to required for move action")
                    return 1
                args.move_to.mkdir(parents=True, exist_ok=True)
                dest = args.move_to / path.name
                shutil.move(str(path), str(dest))
                logger.info(f"Moved: {path} -> {dest}")
            elif args.action == "hardlink":
                # Find the file to keep (not in to_delete)
                for files in duplicates.values():
                    if path in [f.path for f in files]:
                        keep_file = next(f.path for f in files if f.path not in to_delete)
                        path.unlink()
                        path.hardlink_to(keep_file)
                        logger.info(f"Hardlinked: {path} -> {keep_file}")
                        break
        except (PermissionError, OSError) as e:
            logger.error(f"Failed to {args.action} {path}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

