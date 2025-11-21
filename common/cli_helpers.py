"""Shared CLI utilities for consistent argument parsing."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional


def add_log_level_argument(parser: argparse.ArgumentParser) -> None:
    """Add standard --log-level argument.

    Args:
        parser: ArgumentParser to add the argument to
    """
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )


def setup_logging(level: str) -> None:
    """Configure logging with consistent format.

    Args:
        level: Logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_input(file_path: Optional[Path] = None, stdin_marker: str = "-") -> str:
    """Read from file, stdin, or return empty string.

    Args:
        file_path: Path to file, or stdin_marker for stdin
        stdin_marker: String that indicates stdin should be used (default: "-")

    Returns:
        Content as string
    """
    if file_path is None:
        return ""

    if str(file_path) == stdin_marker:
        return sys.stdin.read()

    return Path(file_path).read_text()


def add_json_output_argument(parser: argparse.ArgumentParser) -> None:
    """Add standard --json output flag.

    Args:
        parser: ArgumentParser to add the argument to
    """
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )


def add_dry_run_argument(parser: argparse.ArgumentParser) -> None:
    """Add standard --dry-run flag.

    Args:
        parser: ArgumentParser to add the argument to
    """
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

