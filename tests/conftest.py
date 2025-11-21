"""Shared pytest fixtures for pyutils tests."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterator

import pytest
from PIL import Image


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to sample text file
    """
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello, World!\nThis is a test file.\n")
    return file_path


@pytest.fixture
def sample_image_file(tmp_path: Path) -> Path:
    """Create a sample image file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to sample image file (PNG)
    """
    img = Image.new("RGB", (100, 100), color="red")
    file_path = tmp_path / "sample.png"
    img.save(file_path)
    return file_path


@pytest.fixture
def sample_csv_file(tmp_path: Path) -> Path:
    """Create a sample CSV file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to sample CSV file
    """
    file_path = tmp_path / "sample.csv"
    content = """name,age,email
John Doe,30,john@example.com
Jane Smith,25,jane@example.com
Bob Johnson,35,bob@example.com
"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """Create a sample JSON file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to sample JSON file
    """
    file_path = tmp_path / "sample.json"
    content = """{
  "users": [
    {"name": "John", "age": 30},
    {"name": "Jane", "age": 25}
  ],
  "count": 2
}"""
    file_path.write_text(content)
    return file_path


@pytest.fixture
def multiple_files(tmp_path: Path) -> Iterator[Path]:
    """Create multiple test files in a directory.

    Args:
        tmp_path: Pytest temporary directory fixture

    Yields:
        Path to directory containing test files
    """
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()

    # Create various test files
    (test_dir / "file1.txt").write_text("Content 1")
    (test_dir / "file2.txt").write_text("Content 2")
    (test_dir / "file3.log").write_text("Log content")

    # Create a subdirectory
    subdir = test_dir / "subdir"
    subdir.mkdir()
    (subdir / "file4.txt").write_text("Content 4")

    yield test_dir


@pytest.fixture
def duplicate_files(tmp_path: Path) -> dict[str, list[Path]]:
    """Create duplicate files for testing duplicate detection.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Dict mapping content to list of file paths with that content
    """
    test_dir = tmp_path / "duplicates"
    test_dir.mkdir()

    # Create files with duplicate content
    content_a = "This is content A"
    content_b = "This is content B"

    file1 = test_dir / "file1.txt"
    file2 = test_dir / "file2.txt"
    file3 = test_dir / "file3.txt"
    file4 = test_dir / "subdir" / "file4.txt"

    file4.parent.mkdir()

    file1.write_text(content_a)
    file2.write_text(content_a)  # Duplicate of file1
    file3.write_text(content_b)
    file4.write_text(content_a)  # Another duplicate of file1

    return {
        content_a: [file1, file2, file4],
        content_b: [file3],
    }

