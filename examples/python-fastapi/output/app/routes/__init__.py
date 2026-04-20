"""SPEC-2026-Q2-001 / AC-4 — Route registration with auth router."""

from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.items import router as items_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(items_router)
