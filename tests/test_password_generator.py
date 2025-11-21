"""Tests for password_generator module."""

from __future__ import annotations

import string

import pytest

from password_generator import (
    AMBIGUOUS_CHARS,
    PasswordGenerationError,
    build_alphabets,
    generate_password,
)


def test_build_alphabets_all():
    """Test building alphabets with all character classes."""
    alphabets = build_alphabets(
        use_lower=True,
        use_upper=True,
        use_digits=True,
        use_symbols=True,
        avoid_ambiguous=False,
    )

    assert len(alphabets) == 4
    assert string.ascii_lowercase in alphabets
    assert string.ascii_uppercase in alphabets
    assert string.digits in alphabets
    assert string.punctuation in alphabets


def test_build_alphabets_lowercase_only():
    """Test building alphabets with only lowercase."""
    alphabets = build_alphabets(
        use_lower=True,
        use_upper=False,
        use_digits=False,
        use_symbols=False,
        avoid_ambiguous=False,
    )

    assert len(alphabets) == 1
    assert alphabets[0] == string.ascii_lowercase


def test_build_alphabets_avoid_ambiguous():
    """Test avoiding ambiguous characters."""
    alphabets = build_alphabets(
        use_lower=True,
        use_upper=True,
        use_digits=True,
        use_symbols=False,
        avoid_ambiguous=True,
    )

    # Check that ambiguous chars are not in any alphabet
    all_chars = "".join(alphabets)
    for char in AMBIGUOUS_CHARS:
        assert char not in all_chars


def test_build_alphabets_none_selected():
    """Test building alphabets with no classes selected."""
    alphabets = build_alphabets(
        use_lower=False,
        use_upper=False,
        use_digits=False,
        use_symbols=False,
        avoid_ambiguous=False,
    )

    assert alphabets == []


def test_generate_password_basic():
    """Test basic password generation."""
    password = generate_password(length=16)

    assert len(password) == 16
    assert isinstance(password, str)


def test_generate_password_length():
    """Test password generation with various lengths."""
    for length in [8, 12, 16, 20, 32]:
        password = generate_password(length=length)
        assert len(password) == length


def test_generate_password_lowercase_only():
    """Test password with only lowercase characters."""
    password = generate_password(
        length=16,
        use_lower=True,
        use_upper=False,
        use_digits=False,
        use_symbols=False,
        require_each_class=False,
    )

    assert len(password) == 16
    assert password.islower()
    assert password.isalpha()


def test_generate_password_no_symbols():
    """Test password without symbols."""
    password = generate_password(
        length=16,
        use_lower=True,
        use_upper=True,
        use_digits=True,
        use_symbols=False,
    )

    assert len(password) == 16
    assert password.isalnum()


def test_generate_password_require_each_class():
    """Test that password contains at least one character from each class."""
    password = generate_password(
        length=16,
        use_lower=True,
        use_upper=True,
        use_digits=True,
        use_symbols=True,
        require_each_class=True,
    )

    # Check that password contains at least one from each class
    assert any(c in string.ascii_lowercase for c in password)
    assert any(c in string.ascii_uppercase for c in password)
    assert any(c in string.digits for c in password)
    assert any(c in string.punctuation for c in password)


def test_generate_password_avoid_ambiguous():
    """Test password generation avoiding ambiguous characters."""
    # Generate multiple passwords to increase confidence
    for _ in range(10):
        password = generate_password(
            length=20,
            use_lower=True,
            use_upper=True,
            use_digits=True,
            use_symbols=False,
            avoid_ambiguous=True,
        )

        for char in AMBIGUOUS_CHARS:
            assert char not in password


def test_generate_password_invalid_length():
    """Test that zero or negative length raises error."""
    with pytest.raises(PasswordGenerationError, match="length must be > 0"):
        generate_password(length=0)

    with pytest.raises(PasswordGenerationError, match="length must be > 0"):
        generate_password(length=-1)


def test_generate_password_no_classes():
    """Test that selecting no character classes raises error."""
    with pytest.raises(PasswordGenerationError, match="No character classes selected"):
        generate_password(
            length=16,
            use_lower=False,
            use_upper=False,
            use_digits=False,
            use_symbols=False,
        )


def test_generate_password_length_too_short_for_requirements():
    """Test that length too short for each class requirement raises error."""
    # Require 4 classes but only provide length of 3
    with pytest.raises(
        PasswordGenerationError, match="length must be >= number of selected classes"
    ):
        generate_password(
            length=3,
            use_lower=True,
            use_upper=True,
            use_digits=True,
            use_symbols=True,
            require_each_class=True,
        )


def test_generate_password_minimum_length_with_requirements():
    """Test generating password with minimum length equal to class count."""
    password = generate_password(
        length=4,  # Exactly 4 classes
        use_lower=True,
        use_upper=True,
        use_digits=True,
        use_symbols=True,
        require_each_class=True,
    )

    assert len(password) == 4
    # Should have exactly one from each class
    assert sum(c in string.ascii_lowercase for c in password) >= 1
    assert sum(c in string.ascii_uppercase for c in password) >= 1
    assert sum(c in string.digits for c in password) >= 1
    assert sum(c in string.punctuation for c in password) >= 1


def test_generate_password_randomness():
    """Test that multiple passwords are different (high probability)."""
    passwords = {generate_password(length=16) for _ in range(20)}

    # With high probability, all 20 should be unique
    assert len(passwords) == 20


def test_ambiguous_chars_definition():
    """Test that ambiguous chars are defined correctly."""
    assert AMBIGUOUS_CHARS == {"I", "l", "1", "O", "0"}


def test_password_no_require_each_class():
    """Test password generation without requiring each class."""
    # This should work even with length less than class count
    password = generate_password(
        length=2,
        use_lower=True,
        use_upper=True,
        use_digits=True,
        require_each_class=False,
    )

    assert len(password) == 2
    # Password should only contain valid chars from selected classes
    valid_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
    assert all(c in valid_chars for c in password)

