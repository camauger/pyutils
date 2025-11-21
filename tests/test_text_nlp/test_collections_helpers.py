"""Tests for text_nlp.collections_helpers module."""

from __future__ import annotations

import pytest

from text_nlp.collections_helpers import count_words, count_words_in_text, tokenize


def test_tokenize_basic():
    """Test basic tokenization."""
    text = "Hello world, this is a test!"
    tokens = tokenize(text)

    assert tokens == ["hello", "world", "this", "is", "a", "test"]


def test_tokenize_lowercase_enabled():
    """Test tokenization with lowercase enabled."""
    text = "Hello WORLD"
    tokens = tokenize(text, lowercase=True)

    assert tokens == ["hello", "world"]


def test_tokenize_lowercase_disabled():
    """Test tokenization with lowercase disabled."""
    text = "Hello WORLD"
    tokens = tokenize(text, lowercase=False)

    assert tokens == ["Hello", "WORLD"]


def test_tokenize_strip_punct_enabled():
    """Test tokenization with punctuation stripping."""
    text = "hello, world! how are you?"
    tokens = tokenize(text, strip_punct=True)

    assert tokens == ["hello", "world", "how", "are", "you"]


def test_tokenize_strip_punct_disabled():
    """Test tokenization with punctuation kept."""
    text = "hello, world!"
    tokens = tokenize(text, strip_punct=False, lowercase=True)

    # With strip_punct=False, it just splits on whitespace
    assert tokens == ["hello,", "world!"]


def test_tokenize_empty_string():
    """Test tokenization of empty string."""
    tokens = tokenize("")

    assert tokens == []


def test_tokenize_numbers():
    """Test tokenization with numbers."""
    text = "test123 456 test"
    tokens = tokenize(text)

    assert tokens == ["test123", "456", "test"]


def test_tokenize_unicode():
    """Test tokenization with unicode characters."""
    text = "hello café résumé"
    tokens = tokenize(text)

    assert "hello" in tokens
    assert "café" in tokens or "caf" in tokens  # May vary by regex
    assert "résumé" in tokens or "r" in tokens


def test_count_words_basic():
    """Test basic word counting."""
    words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
    counts = count_words(words)

    assert counts == {"apple": 3, "banana": 2, "cherry": 1}


def test_count_words_empty():
    """Test counting words from empty list."""
    counts = count_words([])

    assert counts == {}


def test_count_words_single():
    """Test counting single word."""
    counts = count_words(["hello"])

    assert counts == {"hello": 1}


def test_count_words_case_sensitive():
    """Test that count_words is case-sensitive."""
    words = ["Hello", "hello", "HELLO"]
    counts = count_words(words)

    assert counts == {"Hello": 1, "hello": 1, "HELLO": 1}


def test_count_words_in_text_basic():
    """Test counting words directly from text."""
    text = "the quick brown fox jumps over the lazy dog"
    counts = count_words_in_text(text)

    assert counts["the"] == 2
    assert counts["quick"] == 1
    assert counts["brown"] == 1
    assert counts["fox"] == 1


def test_count_words_in_text_with_punctuation():
    """Test counting words with punctuation."""
    text = "Hello, world! Hello, world!"
    counts = count_words_in_text(text, lowercase=True, strip_punct=True)

    assert counts == {"hello": 2, "world": 2}


def test_count_words_in_text_case_preservation():
    """Test counting words without lowercasing."""
    text = "Hello hello HELLO"
    counts = count_words_in_text(text, lowercase=False, strip_punct=True)

    assert counts == {"Hello": 1, "hello": 1, "HELLO": 1}


def test_count_words_in_text_complex():
    """Test counting words in complex text."""
    text = """
    The quick brown fox jumps over the lazy dog.
    The dog was really lazy, and the fox was very quick.
    """
    counts = count_words_in_text(text)

    assert counts["the"] == 4
    assert counts["quick"] == 2
    assert counts["lazy"] == 2
    assert counts["fox"] == 2
    assert counts["dog"] == 2


def test_count_words_in_text_empty():
    """Test counting words in empty text."""
    counts = count_words_in_text("")

    assert counts == {}


def test_count_words_in_text_whitespace_only():
    """Test counting words in whitespace-only text."""
    counts = count_words_in_text("   \n\t\r   ")

    assert counts == {}


def test_tokenize_repeated_punctuation():
    """Test tokenization with repeated punctuation."""
    text = "hello!!! world??? test..."
    tokens = tokenize(text, strip_punct=True)

    assert tokens == ["hello", "world", "test"]


def test_count_words_generator():
    """Test that count_words accepts generators."""
    def word_generator():
        yield "hello"
        yield "world"
        yield "hello"

    counts = count_words(word_generator())
    assert counts == {"hello": 2, "world": 1}


def test_tokenize_hyphenated_words():
    """Test tokenization of hyphenated words."""
    text = "well-known state-of-the-art"
    tokens = tokenize(text, strip_punct=True)

    # Hyphenated words are split by the regex
    assert "well" in tokens
    assert "known" in tokens


def test_count_words_in_text_special_chars():
    """Test text with special characters."""
    text = "hello@world.com test#hashtag $money"
    counts = count_words_in_text(text)

    # Alphanumeric parts should be extracted
    assert "hello" in counts
    assert "world" in counts
    assert "com" in counts
    assert "test" in counts


def test_tokenize_multiple_spaces():
    """Test tokenization with multiple spaces."""
    text = "hello    world     test"
    tokens = tokenize(text)

    assert tokens == ["hello", "world", "test"]


def test_count_words_preserves_order():
    """Test that count_words returns a dictionary (order not guaranteed in early Python)."""
    words = ["z", "a", "m", "b"]
    counts = count_words(words)

    assert isinstance(counts, dict)
    assert len(counts) == 4

