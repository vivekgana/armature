"""SPEC-2026-Q2-001 / AC-1 — User model for authentication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class User:
    email: str
    hashed_password: str
    id: str = field(default_factory=lambda: str(uuid4()))
    roles: list[str] = field(default_factory=lambda: ["user"])
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
