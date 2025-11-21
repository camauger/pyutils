"""Shared file operation utilities."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import Iterator, List

logger = logging.getLogger(__name__)


def iter_files(
    root: Path,
    recursive: bool = False,
    include: List[str] | None = None,
    exclude: List[str] | None = None,
    follow_symlinks: bool = False,
) -> Iterator[Path]:
    """Iterate files with include/exclude filtering.

    Args:
        root: Root path to search
        recursive: Recurse into subdirectories
        include: List of glob patterns to include
        exclude: List of glob patterns to exclude
        follow_symlinks: Follow symbolic links

    Yields:
        Matching file paths
    """
    include = include or ["*"]
    exclude = exclude or []

    if root.is_file():
        yield root
        return

    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and matches_filters(p, include, exclude):
                yield p
    else:
        for p in root.iterdir():
            if p.is_file() and matches_filters(p, include, exclude):
                yield p


def matches_filters(
    path: Path,
    include: List[str],
    exclude: List[str],
) -> bool:
    """Check if path matches include/exclude patterns.

    Args:
        path: Path to check
        include: List of glob patterns to include
        exclude: List of glob patterns to exclude

    Returns:
        True if path matches filters
    """
    name = path.name

    # Check excludes first
    for pattern in exclude:
        if fnmatch.fnmatch(name, pattern):
            return False

    # Check includes
    for pattern in include:
        if fnmatch.fnmatch(name, pattern):
            return True

    return False


def safe_filename(name: str, replacement: str = "_") -> str:
    """Sanitize filename by replacing invalid characters.

    Args:
        name: Original filename
        replacement: Character to use for invalid chars

    Returns:
        Safe filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, replacement)
    return name.strip(". ")

