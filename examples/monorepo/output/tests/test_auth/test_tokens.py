"""SPEC-2026-Q2-001 / AC-1, AC-2 — Tests for token encode/decode."""

from __future__ import annotations

import pytest

from packages.shared.auth.tokens import decode_token, encode_token


class TestTokenRoundtrip:
    """SPEC-2026-Q2-001 / AC-1"""

    def test_encode_decode_roundtrip(self):
        token = encode_token("user-123", "test@example.com", ["admin"])
        payload = decode_token(token)
        assert payload.sub == "user-123"
        assert payload.email == "test@example.com"
        assert payload.roles == ["admin"]

    def test_token_contains_expiry(self):
        token = encode_token("user-123", "test@example.com", ["user"])
        payload = decode_token(token)
        assert payload.exp > payload.iat


class TestTokenValidation:
    """SPEC-2026-Q2-001 / AC-2"""

    def test_invalid_token_raises(self):
        import jwt
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("not-a-valid-token")

    def test_tampered_token_raises(self):
        import jwt
        token = encode_token("user-123", "test@example.com", ["user"])
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered)
