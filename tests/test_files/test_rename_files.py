"""Tests for files.rename_files module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from files.rename_files import (
    WINDOWS_INVALID_CHARS,
    apply_transformations,
    build_new_name,
    matches_filters,
    sanitize_filename,
)


def test_sanitize_filename_no_invalid_chars():
    """Test sanitizing filename with no invalid characters."""
    assert sanitize_filename("normal_file.txt") == "normal_file.txt"


def test_sanitize_filename_with_invalid_chars():
    """Test sanitizing filename with invalid characters on Windows."""
    if os.name == "nt":
        # On Windows, invalid chars should be replaced
        result = sanitize_filename('file<>:"|?*.txt')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
    else:
        # On non-Windows, should return as-is
        original = 'file<>:"|?*.txt'
        assert sanitize_filename(original) == original


def test_sanitize_filename_windows_invalid_chars():
    """Test that WINDOWS_INVALID_CHARS is correctly defined."""
    assert WINDOWS_INVALID_CHARS == set('<>:"/\\|?*')


def test_apply_transformations_prefix():
    """Test applying prefix transformation."""
    result = apply_transformations(
        stem="test",
        prefix="pre_",
        suffix="",
        find=None,
        replace_with="",
        regex=None,
        regex_repl="",
        lower=False,
        upper=False,
        title=False,
    )
    assert result == "pre_test"


def test_apply_transformations_suffix():
    """Test applying suffix transformation."""
    result = apply_transformations(
        stem="test",
        prefix="",
        suffix="_post",
        find=None,
        replace_with="",
        regex=None,
        regex_repl="",
        lower=False,
        upper=False,
        title=False,
    )
    assert result == "test_post"


def test_apply_transformations_find_replace():
    """Test applying find and replace transformation."""
    result = apply_transformations(
        stem="hello_world",
        prefix="",
        suffix="",
        find="_",
        replace_with="-",
        regex=None,
        regex_repl="",
        lower=False,
        upper=False,
        title=False,
    )
    assert result == "hello-world"


def test_apply_transformations_lowercase():
    """Test applying lowercase transformation."""
    result = apply_transformations(
        stem="HELLO",
        prefix="",
        suffix="",
        find=None,
        replace_with="",
        regex=None,
        regex_repl="",
        lower=True,
        upper=False,
        title=False,
    )
    assert result == "hello"


def test_apply_transformations_uppercase():
    """Test applying uppercase transformation."""
    result = apply_transformations(
        stem="hello",
        prefix="",
        suffix="",
        find=None,
        replace_with="",
        regex=None,
        regex_repl="",
        lower=False,
        upper=True,
        title=False,
    )
    assert result == "HELLO"


def test_apply_transformations_title():
    """Test applying title case transformation."""
    result = apply_transformations(
        stem="hello world",
        prefix="",
        suffix="",
        find=None,
        replace_with="",
        regex=None,
        regex_repl="",
        lower=False,
        upper=False,
        title=True,
    )
    assert result == "Hello World"


def test_apply_transformations_regex():
    """Test applying regex transformation."""
    result = apply_transformations(
        stem="file123",
        prefix="",
        suffix="",
        find=None,
        replace_with="",
        regex=r"(\d+)",
        regex_repl=r"[\1]",
        lower=False,
        upper=False,
        title=False,
    )
    assert result == "file[123]"


def test_apply_transformations_invalid_regex():
    """Test that invalid regex raises ValueError."""
    with pytest.raises(ValueError, match="Invalid regex"):
        apply_transformations(
            stem="test",
            prefix="",
            suffix="",
            find=None,
            replace_with="",
            regex="[invalid(regex",
            regex_repl="",
            lower=False,
            upper=False,
            title=False,
        )


def test_apply_transformations_combined():
    """Test applying multiple transformations together."""
    result = apply_transformations(
        stem="hello_WORLD",
        prefix="pre_",
        suffix="_post",
        find="_",
        replace_with="-",
        regex=None,
        regex_repl="",
        lower=True,
        upper=False,
        title=False,
    )
    assert result == "pre_hello-world_post"


def test_apply_transformations_order():
    """Test that transformations are applied in correct order."""
    # find/replace happens before case transform
    result = apply_transformations(
        stem="HELLO_WORLD",
        prefix="",
        suffix="",
        find="_",
        replace_with=" ",
        regex=None,
        regex_repl="",
        lower=True,
        upper=False,
        title=False,
    )
    assert result == "hello world"


def test_build_new_name_no_template(tmp_path: Path):
    """Test building new name without template."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    new_name = build_new_name(
        path=test_file,
        stem_transform="renamed",
        ext=".txt",
        template=None,
        seq_num=None,
        pad=3,
    )

    assert new_name == "renamed.txt"


def test_build_new_name_with_template(tmp_path: Path):
    """Test building new name with template."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    new_name = build_new_name(
        path=test_file,
        stem_transform="original",
        ext=".txt",
        template="{n}_{stem}{ext}",
        seq_num=5,
        pad=3,
    )

    assert new_name == "005_original.txt"


def test_build_new_name_with_sequence_number(tmp_path: Path):
    """Test building new name with sequence number and no template."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    new_name = build_new_name(
        path=test_file,
        stem_transform="file",
        ext=".txt",
        template=None,
        seq_num=42,
        pad=4,
    )

    assert new_name == "0042_file.txt"


def test_build_new_name_template_tokens(tmp_path: Path):
    """Test all template tokens."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.touch()

    new_name = build_new_name(
        path=test_file,
        stem_transform="transformed",
        ext=".md",
        template="{parent}_{stem}_{n}{ext}",
        seq_num=1,
        pad=2,
    )

    assert new_name == "subdir_transformed_01.md"


def test_matches_filters_no_filters(tmp_path: Path):
    """Test file matching with no filters."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    assert matches_filters(test_file, tmp_path, [], [], [])


def test_matches_filters_include_glob(tmp_path: Path):
    """Test file matching with include glob."""
    txt_file = tmp_path / "test.txt"
    log_file = tmp_path / "test.log"
    txt_file.touch()
    log_file.touch()

    assert matches_filters(txt_file, tmp_path, ["*.txt"], [], [])
    assert not matches_filters(log_file, tmp_path, ["*.txt"], [], [])


def test_matches_filters_exclude_glob(tmp_path: Path):
    """Test file matching with exclude glob."""
    test1 = tmp_path / "test1.txt"
    temp1 = tmp_path / "temp1.txt"
    test1.touch()
    temp1.touch()

    assert matches_filters(test1, tmp_path, [], ["temp*"], [])
    assert not matches_filters(temp1, tmp_path, [], ["temp*"], [])


def test_matches_filters_extension_filter(tmp_path: Path):
    """Test file matching with extension filter."""
    txt_file = tmp_path / "test.txt"
    log_file = tmp_path / "test.log"
    txt_file.touch()
    log_file.touch()

    assert matches_filters(txt_file, tmp_path, [], [], [".txt"])
    assert not matches_filters(log_file, tmp_path, [], [], [".txt"])


def test_matches_filters_case_insensitive_extension(tmp_path: Path):
    """Test extension filter is case-insensitive."""
    upper_file = tmp_path / "test.TXT"
    lower_file = tmp_path / "test.txt"
    upper_file.touch()
    lower_file.touch()

    assert matches_filters(upper_file, tmp_path, [], [], [".txt"])
    assert matches_filters(lower_file, tmp_path, [], [], [".TXT"])


def test_matches_filters_combined(tmp_path: Path):
    """Test file matching with multiple filters."""
    file1 = tmp_path / "test.txt"
    file2 = tmp_path / "exclude.txt"
    file3 = tmp_path / "test.log"

    file1.touch()
    file2.touch()
    file3.touch()

    # Include .txt, exclude files starting with 'exclude'
    assert matches_filters(file1, tmp_path, ["*.txt"], ["exclude*"], [])
    assert not matches_filters(file2, tmp_path, ["*.txt"], ["exclude*"], [])
    assert not matches_filters(file3, tmp_path, ["*.txt"], ["exclude*"], [])

