"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-3, AC-4, AC-5 — Auth middleware for FastAPI and Celery."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import jwt as pyjwt
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from packages.shared.auth.tokens import TokenPayload, decode_token


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates JWT from Authorization header.

    AC-1: Validates JWT tokens from Authorization header.
    AC-2: Invalid tokens return 401 with structured error response.
    AC-3: User context (id, roles) available in request.state after auth.
    """

    def __init__(self, app: Any, *, exclude_paths: list[str] | None = None) -> None:
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or [])

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "missing_token", "message": "Bearer token required"},
            )

        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except pyjwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "invalid_token", "message": str(e)},
            )

        request.state.user = payload
        return await call_next(request)


def require_auth(func: Callable) -> Callable:
    """Decorator for Celery tasks and worker functions that validates webhook tokens.

    AC-5: Worker service uses shared middleware for webhook validation.
    Expects a `token` keyword argument in the decorated function.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = kwargs.get("token")
        if not token:
            raise PermissionError("Authentication token required")
        try:
            payload = decode_token(token)
        except pyjwt.InvalidTokenError as e:
            raise PermissionError(f"Invalid token: {e}")
        kwargs["user"] = payload
        return func(*args, **kwargs)

    return wrapper
