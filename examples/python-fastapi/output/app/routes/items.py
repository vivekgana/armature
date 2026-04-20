"""SPEC-2026-Q2-002 / AC-1, AC-2, AC-3 — Items endpoint with fixed pagination."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["items"])

_ITEMS: list[dict] = [{"id": i, "name": f"Item {i}"} for i in range(1, 101)]


class PaginatedResponse(BaseModel):
    items: list[dict]
    page: int
    limit: int
    total: int


@router.get("/", response_model=PaginatedResponse)
def list_items(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> PaginatedResponse:
    """Return paginated items.

    Fix: offset is now `(page - 1) * limit` instead of `(page - 1) * limit + 1`.
    AC-1: Page 2 with limit=10 returns items 11-20.
    AC-2: Last page returns remaining items without gaps.
    AC-3: Page 1 behavior unchanged.
    """
    offset = (page - 1) * limit
    return PaginatedResponse(
        items=_ITEMS[offset : offset + limit],
        page=page,
        limit=limit,
        total=len(_ITEMS),
    )
