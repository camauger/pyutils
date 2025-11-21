"""Tests for files.pathfinder module."""

from __future__ import annotations

from pathlib import Path

import pytest

from files.pathfinder import PathError, cmd_info, cmd_ls, human_size


def test_human_size_bytes():
    """Test human size formatting for bytes."""
    assert human_size(0) == "0.0 B"
    assert human_size(100) == "100.0 B"
    assert human_size(1023) == "1023.0 B"


def test_human_size_kilobytes():
    """Test human size formatting for kilobytes."""
    assert human_size(1024) == "1.0 KB"
    assert human_size(2048) == "2.0 KB"
    assert human_size(1536) == "1.5 KB"


def test_human_size_megabytes():
    """Test human size formatting for megabytes."""
    assert human_size(1024 * 1024) == "1.0 MB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_human_size_gigabytes():
    """Test human size formatting for gigabytes."""
    assert human_size(1024 * 1024 * 1024) == "1.0 GB"
    assert human_size(3 * 1024 * 1024 * 1024) == "3.0 GB"


def test_human_size_terabytes():
    """Test human size formatting for terabytes."""
    assert human_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


def test_cmd_info_file(sample_text_file: Path):
    """Test getting info about a file."""
    info = cmd_info(sample_text_file)

    assert info["path"] == str(sample_text_file)
    assert info["name"] == "sample.txt"
    assert info["suffix"] == ".txt"
    assert info["exists"] is True
    assert info["is_file"] is True
    assert info["is_dir"] is False
    assert "size_bytes" in info
    assert "size_human" in info


def test_cmd_info_directory(tmp_path: Path):
    """Test getting info about a directory."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    info = cmd_info(test_dir)

    assert info["name"] == "test_dir"
    assert info["exists"] is True
    assert info["is_file"] is False
    assert info["is_dir"] is True


def test_cmd_info_nonexistent(tmp_path: Path):
    """Test getting info about nonexistent path."""
    nonexistent = tmp_path / "does_not_exist.txt"

    info = cmd_info(nonexistent)

    assert info["exists"] is False
    assert info["is_file"] is False
    assert info["is_dir"] is False


def test_cmd_info_absolute_path(sample_text_file: Path):
    """Test that absolute path is included in info."""
    info = cmd_info(sample_text_file)

    assert "absolute" in info
    assert Path(info["absolute"]).is_absolute()


def test_cmd_ls_basic(multiple_files: Path):
    """Test listing files in a directory."""
    files = cmd_ls(multiple_files, recursive=False, glob_pattern=None, files_only=False, dirs_only=False)

    # Should list files and subdirectory
    assert len(files) >= 3  # At least 3 files + 1 subdir


def test_cmd_ls_files_only(multiple_files: Path):
    """Test listing only files."""
    files = cmd_ls(multiple_files, recursive=False, glob_pattern=None, files_only=True, dirs_only=False)

    # Should only include files, not directories
    for file in files:
        assert Path(file).is_file()


def test_cmd_ls_dirs_only(multiple_files: Path):
    """Test listing only directories."""
    dirs = cmd_ls(multiple_files, recursive=False, glob_pattern=None, files_only=False, dirs_only=True)

    # Should only include directories
    for dir_path in dirs:
        assert Path(dir_path).is_dir()


def test_cmd_ls_recursive(multiple_files: Path):
    """Test recursive directory listing."""
    files = cmd_ls(multiple_files, recursive=True, glob_pattern=None, files_only=True, dirs_only=False)

    # Should include file4.txt from subdirectory
    assert any("file4.txt" in f for f in files)


def test_cmd_ls_glob_pattern(multiple_files: Path):
    """Test listing with glob pattern."""
    files = cmd_ls(multiple_files, recursive=False, glob_pattern="*.txt", files_only=False, dirs_only=False)

    # Should only include .txt files
    for file in files:
        assert file.endswith(".txt")


def test_cmd_ls_nonexistent_dir(tmp_path: Path):
    """Test listing nonexistent directory raises error."""
    nonexistent = tmp_path / "does_not_exist"

    with pytest.raises(PathError, match="not a directory"):
        cmd_ls(nonexistent, recursive=False, glob_pattern=None, files_only=False, dirs_only=False)


def test_cmd_ls_file_not_dir(sample_text_file: Path):
    """Test that listing a file (not directory) raises error."""
    with pytest.raises(PathError, match="not a directory"):
        cmd_ls(sample_text_file, recursive=False, glob_pattern=None, files_only=False, dirs_only=False)


def test_cmd_ls_empty_directory(tmp_path: Path):
    """Test listing empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    files = cmd_ls(empty_dir, recursive=False, glob_pattern=None, files_only=False, dirs_only=False)

    assert files == []


def test_cmd_ls_glob_no_matches(multiple_files: Path):
    """Test glob pattern with no matches."""
    files = cmd_ls(multiple_files, recursive=False, glob_pattern="*.xyz", files_only=False, dirs_only=False)

    assert files == []


def test_cmd_info_file_size(tmp_path: Path):
    """Test that file size is correctly reported."""
    test_file = tmp_path / "sized_file.txt"
    content = "A" * 1000  # 1000 bytes
    test_file.write_text(content)

    info = cmd_info(test_file)

    assert info["size_bytes"] == 1000
    assert "size_human" in info


def test_human_size_zero():
    """Test human size for zero bytes."""
    assert human_size(0) == "0.0 B"


def test_cmd_info_parent(sample_text_file: Path):
    """Test that parent path is included in info."""
    info = cmd_info(sample_text_file)

    assert "parent" in info
    assert Path(info["parent"]) == sample_text_file.parent


def test_cmd_ls_mixed_files_and_dirs(multiple_files: Path):
    """Test listing both files and directories."""
    all_items = cmd_ls(multiple_files, recursive=False, glob_pattern=None, files_only=False, dirs_only=False)

    # Should include both files and directories
    assert len(all_items) >= 4  # At least 3 files + 1 subdir

