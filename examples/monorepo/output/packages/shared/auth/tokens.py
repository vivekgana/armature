"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-3 — JWT token handling (RS256 + HS256)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt


@dataclass
class TokenPayload:
    sub: str
    email: str
    roles: list[str]
    exp: datetime
    iat: datetime


JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
TOKEN_TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "24"))

_SUPPORTED_ALGORITHMS = ["HS256", "RS256"]


def encode_token(
    user_id: str,
    email: str,
    roles: list[str],
    *,
    ttl_hours: int | None = None,
) -> str:
    """Create a signed JWT token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "exp": now + timedelta(hours=ttl_hours or TOKEN_TTL_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT. Supports both RS256 and HS256.

    Raises jwt.InvalidTokenError on any validation failure.
    """
    if JWT_ALGORITHM == "RS256" and JWT_PUBLIC_KEY:
        key = JWT_PUBLIC_KEY
    else:
        key = JWT_SECRET

    data = jwt.decode(token, key, algorithms=_SUPPORTED_ALGORITHMS)
    return TokenPayload(
        sub=data["sub"],
        email=data["email"],
        roles=data.get("roles", []),
        exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
        iat=datetime.fromtimestamp(data["iat"], tz=timezone.utc),
    )
