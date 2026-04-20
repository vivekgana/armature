"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-5 — Tests for auth middleware and require_auth."""

from __future__ import annotations

import pytest

from packages.shared.auth.middleware import require_auth
from packages.shared.auth.tokens import encode_token


class TestRequireAuth:
    """SPEC-2026-Q2-001 / AC-5"""

    def test_valid_token_passes(self):
        token = encode_token("worker-user", "worker@example.com", ["worker"])

        @require_auth
        def task(data: str, *, token: str = "", user=None):
            return {"data": data, "user_id": user.sub}

        result = task("test-payload", token=token)
        assert result["user_id"] == "worker-user"
        assert result["data"] == "test-payload"

    def test_missing_token_raises(self):
        @require_auth
        def task(data: str, *, token: str = "", user=None):
            return data

        with pytest.raises(PermissionError, match="token required"):
            task("payload")

    def test_invalid_token_raises(self):
        @require_auth
        def task(data: str, *, token: str = "", user=None):
            return data

        with pytest.raises(PermissionError, match="Invalid token"):
            task("payload", token="bad-token")
