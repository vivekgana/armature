"""SPEC-2026-Q2-001 / AC-4 — API service using shared auth middleware."""

from __future__ import annotations

from fastapi import FastAPI, Request

from packages.shared.auth import AuthMiddleware

app = FastAPI(title="API Service")

app.add_middleware(
    AuthMiddleware,
    exclude_paths=["/health", "/auth/login", "/auth/register"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/me")
async def get_current_user(request: Request) -> dict:
    """AC-3: User context available in request after auth."""
    user = request.state.user
    return {"id": user.sub, "email": user.email, "roles": user.roles}


@app.get("/items")
async def list_items(request: Request) -> dict:
    return {"items": [], "user": request.state.user.sub}
