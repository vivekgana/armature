"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-3, AC-5 — Unit tests for auth service."""

from __future__ import annotations

import pytest

from app.services.auth_service import authenticate, register, verify_token


class TestRegister:
    """SPEC-2026-Q2-001 / AC-1"""

    def test_register_creates_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        user = register("test@example.com", "password123")
        assert user.email == "test@example.com"
        assert user.id
        assert user.roles == ["user"]

    def test_register_duplicate_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        register("dup@example.com", "pass")
        with pytest.raises(ValueError, match="already exists"):
            register("dup@example.com", "pass")


class TestAuthenticate:
    """SPEC-2026-Q2-001 / AC-2, AC-3"""

    def test_valid_credentials_return_token(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        register("user@example.com", "secret")
        token = authenticate("user@example.com", "secret")
        assert token is not None
        payload = verify_token(token)
        assert payload["email"] == "user@example.com"

    def test_invalid_password_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        register("user@example.com", "correct")
        assert authenticate("user@example.com", "wrong") is None

    def test_unknown_user_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        assert authenticate("nobody@example.com", "pass") is None


class TestTokenExpiry:
    """SPEC-2026-Q2-001 / AC-5"""

    def test_token_contains_exp_claim(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.USERS_FILE", tmp_path / "users.json")
        register("exp@example.com", "pass")
        token = authenticate("exp@example.com", "pass")
        payload = verify_token(token)
        assert "exp" in payload
