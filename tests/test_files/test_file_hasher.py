"""Tests for files.file_hasher module."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from files.file_hasher import (
    HashRecord,
    hash_file,
    make_record,
    matches_filters,
)


def test_hash_file_sha256(tmp_path: Path):
    """Test SHA256 hashing of a known file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    digest = hash_file(test_file, "sha256")

    # Known SHA256 of "Hello, World!"
    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert digest == expected


def test_hash_file_md5(tmp_path: Path):
    """Test MD5 hashing of a known file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    digest = hash_file(test_file, "md5")

    # Known MD5 of "Hello, World!"
    expected = "65a8e27d8879283831b664bd8b7f0ad4"
    assert digest == expected


@pytest.mark.parametrize(
    "algo,expected",
    [
        ("sha256", "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"),
        ("md5", "65a8e27d8879283831b664bd8b7f0ad4"),
        ("sha1", "0a0a9f2a6772942557ab5355d76af442f8f65e01"),
    ],
)
def test_hash_algorithms(tmp_path: Path, algo: str, expected: str):
    """Test multiple hashing algorithms."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    digest = hash_file(test_file, algo)
    assert digest == expected


def test_hash_file_empty(tmp_path: Path):
    """Test hashing an empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")

    digest = hash_file(test_file, "sha256")

    # SHA256 of empty file
    expected = hashlib.sha256(b"").hexdigest()
    assert digest == expected


def test_hash_file_binary(tmp_path: Path):
    """Test hashing a binary file."""
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

    digest = hash_file(test_file, "sha256")

    # Calculate expected hash
    expected = hashlib.sha256(b"\x00\x01\x02\x03\xff\xfe\xfd").hexdigest()
    assert digest == expected


def test_make_record_relative(tmp_path: Path):
    """Test creating hash record with relative paths."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    record = make_record(test_file, tmp_path, "sha256", relative_paths=True)

    assert record.path == "test.txt"
    assert record.algo == "sha256"
    assert len(record.digest) == 64  # SHA256 hex length


def test_make_record_absolute(tmp_path: Path):
    """Test creating hash record with absolute paths."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    record = make_record(test_file, tmp_path, "sha256", relative_paths=False)

    assert Path(record.path).is_absolute()
    assert record.algo == "sha256"
    assert len(record.digest) == 64


def test_matches_filters_no_filters(tmp_path: Path):
    """Test file matching with no filters."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    assert matches_filters(test_file, tmp_path, [], [])


def test_matches_filters_include(tmp_path: Path):
    """Test file matching with include patterns."""
    txt_file = tmp_path / "test.txt"
    log_file = tmp_path / "test.log"
    txt_file.write_text("content")
    log_file.write_text("content")

    # Only .txt files
    assert matches_filters(txt_file, tmp_path, ["*.txt"], [])
    assert not matches_filters(log_file, tmp_path, ["*.txt"], [])


def test_matches_filters_exclude(tmp_path: Path):
    """Test file matching with exclude patterns."""
    txt_file = tmp_path / "test.txt"
    log_file = tmp_path / "test.log"
    txt_file.write_text("content")
    log_file.write_text("content")

    # Exclude .log files
    assert matches_filters(txt_file, tmp_path, [], ["*.log"])
    assert not matches_filters(log_file, tmp_path, [], ["*.log"])


def test_matches_filters_include_and_exclude(tmp_path: Path):
    """Test file matching with both include and exclude patterns."""
    file1 = tmp_path / "test.txt"
    file2 = tmp_path / "exclude.txt"
    file3 = tmp_path / "test.log"

    file1.write_text("content")
    file2.write_text("content")
    file3.write_text("content")

    # Include .txt but exclude files starting with 'exclude'
    assert matches_filters(file1, tmp_path, ["*.txt"], ["exclude*"])
    assert not matches_filters(file2, tmp_path, ["*.txt"], ["exclude*"])
    assert not matches_filters(file3, tmp_path, ["*.txt"], ["exclude*"])


def test_hash_record_frozen():
    """Test that HashRecord is immutable."""
    record = HashRecord(path="test.txt", algo="sha256", digest="abc123")

    with pytest.raises(AttributeError):
        record.path = "new_path.txt"  # type: ignore


def test_hash_large_file(tmp_path: Path):
    """Test hashing a large file to ensure chunked reading works."""
    test_file = tmp_path / "large.bin"

    # Create a file larger than the chunk size (1MB in hash_file)
    large_content = b"A" * (2 * 1024 * 1024)  # 2MB
    test_file.write_bytes(large_content)

    digest = hash_file(test_file, "sha256")
    expected = hashlib.sha256(large_content).hexdigest()

    assert digest == expected

