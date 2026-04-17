"""Core business logic for expense tracking."""

from decimal import Decimal


def add_expense(data, amount, category, description="", date=None):
    """Add an expense record."""
    expense_id = data["next_id"]
    record = {
        "id": expense_id,
        "date": date or "2026-01-01",
        "amount": str(amount),
        "category": category,
        "description": description,
    }
    data["next_id"] += 1
    data["expenses"].append(record)
    return data, record


def list_expenses(data, category=None):
    """List expenses with optional filter."""
    expenses = data["expenses"]
    if category:
        expenses = [e for e in expenses if e["category"] == category]
    return expenses


def summarize(data):
    """Summarize spending by category."""
    totals = {}
    for e in data["expenses"]:
        cat = e["category"]
        totals[cat] = totals.get(cat, Decimal("0")) + Decimal(e["amount"])
    return totals
