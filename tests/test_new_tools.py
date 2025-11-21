"""Tests for new data processing tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from data.csv_tools import filter_rows, get_stats, select_columns, to_markdown_table
from data.json_tools import flatten_json, query_json


def test_csv_filter_rows():
    """Test CSV row filtering."""
    data = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
        {"name": "Charlie", "age": "35"},
    ]

    filtered = filter_rows(data, "age", "gt", "28")
    assert len(filtered) == 2
    assert filtered[0]["name"] == "Alice"


def test_csv_select_columns():
    """Test CSV column selection."""
    data = [
        {"name": "Alice", "age": "30", "city": "NYC"},
        {"name": "Bob", "age": "25", "city": "LA"},
    ]

    selected = select_columns(data, ["name", "city"])
    assert len(selected) == 2
    assert "age" not in selected[0]
    assert "name" in selected[0]


def test_csv_get_stats():
    """Test CSV statistics."""
    data = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
        {"name": "Alice", "age": "30"},
    ]

    stats = get_stats(data)
    assert stats["row_count"] == 3
    assert stats["column_count"] == 2
    assert stats["unique_values"]["name"] == 2  # Alice and Bob


def test_csv_to_markdown():
    """Test CSV to Markdown conversion."""
    data = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
    ]

    md = to_markdown_table(data)
    assert "| name | age |" in md
    assert "| Alice | 30 |" in md


def test_json_query_basic():
    """Test basic JSON querying."""
    data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}

    result = query_json(data, "users")
    assert len(result) == 2

    result = query_json(data, "users.0.name")
    assert result == "Alice"


def test_json_query_missing_path():
    """Test JSON query with missing path."""
    data = {"users": [{"name": "Alice"}]}

    result = query_json(data, "missing")
    assert result is None


def test_json_flatten():
    """Test JSON flattening."""
    data = {"user": {"name": "Alice", "address": {"city": "NYC", "zip": "10001"}}}

    flat = flatten_json(data)
    assert "user.name" in flat
    assert flat["user.name"] == "Alice"
    assert "user.address.city" in flat
    assert flat["user.address.city"] == "NYC"


def test_json_flatten_list():
    """Test JSON flattening with lists."""
    data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}

    flat = flatten_json(data)
    assert "users.0.name" in flat
    assert flat["users.0.name"] == "Alice"
    assert "users.1.name" in flat
    assert flat["users.1.name"] == "Bob"


# Simplified tests for duplicate_finder
def test_duplicate_finder_hash(tmp_path: Path):
    """Test file hashing for duplicate detection."""
    from files.duplicate_finder import hash_file

    file1 = tmp_path / "test1.txt"
    file1.write_text("content")

    hash1 = hash_file(file1)
    assert len(hash1) == 64  # SHA256 hex length


def test_duplicate_finder_find_duplicates(tmp_path: Path, duplicate_files: dict):
    """Test finding duplicate files."""
    from files.duplicate_finder import find_duplicates

    # Use the duplicate_files fixture from conftest
    test_dir = list(duplicate_files.values())[0][0].parent

    duplicates = find_duplicates(test_dir, recursive=True, min_size=0)

    # Should find at least one group of duplicates
    assert len(duplicates) >= 1

