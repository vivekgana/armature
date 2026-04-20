"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-3, AC-5 — JWT auth service."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from passlib.hash import bcrypt

from app.models.user import User

USERS_FILE = Path("data/users.json")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "24"))


def _load_users() -> dict[str, dict]:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def _save_users(users: dict[str, dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def register(email: str, password: str) -> User:
    users = _load_users()
    if email in users:
        raise ValueError(f"User {email} already exists")
    user = User(email=email, hashed_password=bcrypt.hash(password))
    users[email] = {
        "id": user.id,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "roles": user.roles,
        "created_at": user.created_at,
    }
    _save_users(users)
    return user


def authenticate(email: str, password: str) -> str | None:
    """Return a JWT token if credentials are valid, None otherwise."""
    users = _load_users()
    record = users.get(email)
    if record is None or not bcrypt.verify(password, record["hashed_password"]):
        return None
    payload = {
        "sub": record["id"],
        "email": email,
        "roles": record["roles"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
