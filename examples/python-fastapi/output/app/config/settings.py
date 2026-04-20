"""SPEC-2026-Q2-001 — Application settings with JWT configuration."""

from __future__ import annotations

import os


APP_NAME = "my-fastapi-app"
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
TOKEN_TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "24"))
