"""Path utilities CLI: info, list, read, and join with logging.

Examples:
  - Info: python pathfinder.py info ./some/path
  - List: python pathfinder.py ls . --recursive --glob "*.py" --json
  - Read: python pathfinder.py read ./README.md
  - Join: python pathfinder.py join /base dir file.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


class PathError(RuntimeError):
    """Raised when a path operation fails."""


def human_size(num_bytes: int) -> str:
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < step:
            return f"{size:.1f} {unit}"
        size /= step
    return f"{size:.1f} PB"


def cmd_info(path: Path) -> dict:
    info = {
        "path": str(path),
        "absolute": str(path.resolve()),
        "name": path.name,
        "parent": str(path.parent),
        "suffix": path.suffix,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }
    try:
        if path.exists() and path.is_file():
            size = path.stat().st_size
            info["size_bytes"] = size
            info["size_human"] = human_size(size)
    except Exception:  # noqa: BLE001
        pass
    return info


def iter_dir(path: Path, recursive: bool) -> Iterable[Path]:
    return (p for p in (path.rglob("*") if recursive else path.glob("*")))


def cmd_ls(
    path: Path,
    recursive: bool,
    glob_pattern: Optional[str],
    files_only: bool,
    dirs_only: bool,
) -> List[str]:
    if not path.exists() or not path.is_dir():
        raise PathError(f"Path is not a directory: {path}")
    entries: List[Path] = list(iter_dir(path, recursive))
    if glob_pattern:
        entries = [p for p in entries if p.match(glob_pattern)]
    if files_only:
        entries = [p for p in entries if p.is_file()]
    if dirs_only:
        entries = [p for p in entries if p.is_dir()]
    return [str(p) for p in entries]


def cmd_read(path: Path, encoding: str) -> str:
    if not path.exists() or not path.is_file():
        raise PathError(f"Not a file: {path}")
    try:
        return path.read_text(encoding=encoding)
    except Exception as ex:  # noqa: BLE001
        raise PathError(f"Failed to read file '{path}': {ex}") from ex


def cmd_join(base: Path, parts: List[str]) -> str:
    p = base
    for part in parts:
        p = p / part
    return str(p)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Path utilities (info, ls, read, join)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Show information about a path")
    p_info.add_argument("path", type=Path)

    p_ls = sub.add_parser("ls", help="List directory contents")
    p_ls.add_argument("path", type=Path)
    p_ls.add_argument("--recursive", action="store_true")
    p_ls.add_argument("--glob", type=str, help="Glob pattern to filter results")
    p_ls.add_argument("--files-only", action="store_true")
    p_ls.add_argument("--dirs-only", action="store_true")
    p_ls.add_argument("--json", action="store_true", help="Output JSON array")

    p_read = sub.add_parser("read", help="Read a text file")
    p_read.add_argument("path", type=Path)
    p_read.add_argument("--encoding", type=str, default="utf-8")

    p_join = sub.add_parser("join", help="Join paths from a base and parts")
    p_join.add_argument("base", type=Path)
    p_join.add_argument("parts", nargs="+", type=str)

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
        if args.command == "info":
            result = cmd_info(args.path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "ls":
            entries = cmd_ls(
                path=args.path,
                recursive=args.recursive,
                glob_pattern=args.glob,
                files_only=args.files_only,
                dirs_only=args.dirs_only,
            )
            if args.json:
                print(json.dumps(entries, ensure_ascii=False))
            else:
                for e in entries:
                    print(e)
            return 0
        if args.command == "read":
            content = cmd_read(args.path, args.encoding)
            print(content)
            return 0
        if args.command == "join":
            print(cmd_join(args.base, args.parts))
            return 0
    except PathError as ex:
        logger.error(str(ex))
        return 1

    logger.error("Unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
