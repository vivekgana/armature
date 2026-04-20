"""SPEC-2026-Q2-002 / AC-1, AC-2, AC-3 — Regression tests for pagination fix."""

from __future__ import annotations

from app.routes.items import _ITEMS, list_items


class TestPaginationFix:
    """SPEC-2026-Q2-002 / AC-1"""

    def test_page_2_returns_items_11_to_20(self):
        result = list_items(page=2, limit=10)
        ids = [item["id"] for item in result.items]
        assert ids == list(range(11, 21))

    def test_page_1_returns_items_1_to_10(self):
        """SPEC-2026-Q2-002 / AC-3"""
        result = list_items(page=1, limit=10)
        ids = [item["id"] for item in result.items]
        assert ids == list(range(1, 11))

    def test_last_page_no_gaps(self):
        """SPEC-2026-Q2-002 / AC-2"""
        total = len(_ITEMS)
        limit = 10
        all_ids = []
        page = 1
        while True:
            result = list_items(page=page, limit=limit)
            if not result.items:
                break
            all_ids.extend(item["id"] for item in result.items)
            page += 1
        assert all_ids == list(range(1, total + 1))

    def test_total_count_is_correct(self):
        result = list_items(page=1, limit=10)
        assert result.total == 100
