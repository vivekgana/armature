"""SPEC-2026-Q2-001 / AC-5 — Worker service using shared auth for webhook validation."""

from __future__ import annotations

from packages.shared.auth import require_auth


@require_auth
def process_webhook(payload: dict, *, token: str = "", user: object = None) -> dict:
    """AC-5: Worker validates webhook token via shared middleware.

    The @require_auth decorator extracts and validates the JWT,
    then injects the `user` TokenPayload into kwargs.
    """
    return {
        "status": "processed",
        "payload": payload,
        "authenticated_user": user.sub if user else None,
    }


@require_auth
def sync_data(source: str, *, token: str = "", user: object = None) -> dict:
    """Background task that requires authentication."""
    return {
        "status": "synced",
        "source": source,
        "user": user.sub if user else None,
    }
