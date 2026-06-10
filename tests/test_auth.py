"""Tests for auth helpers and form validation."""

import pytest
from app.auth.helpers import hash_password, verify_password
from app.auth.forms import validate_register, validate_login


def test_hash_and_verify():
    """Hash then verify returns True for the same password."""
    hashed = hash_password("StrongPass1!")
    assert verify_password("StrongPass1!", hashed) is True


def test_verify_wrong_password():
    """verify_password returns False for a different password."""
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_validate_register_valid():
    """validate_register returns no errors for well-formed input."""
    errors = validate_register(
        "user@example.com", "password123", "password123", agreed_to_terms=True
    )
    assert errors == []


def test_validate_register_mismatched_passwords():
    """validate_register flags mismatched passwords."""
    errors = validate_register(
        "user@example.com", "abc12345", "abc12346", agreed_to_terms=True
    )
    assert any("match" in e.lower() for e in errors)


def test_validate_register_short_password():
    """validate_register flags passwords under 8 characters."""
    errors = validate_register(
        "user@example.com", "short", "short", agreed_to_terms=True
    )
    assert any("8" in e for e in errors)


def test_validate_login_empty():
    """validate_login flags empty fields."""
    errors = validate_login("", "")
    assert len(errors) == 2
