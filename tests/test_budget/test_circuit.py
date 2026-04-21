"""Tests for budget/circuit.py -- budget circuit breaker."""

from __future__ import annotations

from armature.budget.circuit import BudgetCircuit


class TestBudgetCircuit:
    """Tests for BudgetCircuit dataclass."""

    def test_starts_closed(self):
        circuit = BudgetCircuit()
        assert circuit.is_open is False
        assert circuit.consecutive_over == 0

    def test_opens_after_threshold(self):
        circuit = BudgetCircuit(threshold=3)
        circuit.record(over_budget=True)
        circuit.record(over_budget=True)
        assert circuit.is_open is False
        circuit.record(over_budget=True)
        assert circuit.is_open is True

    def test_resets_on_under_budget(self):
        circuit = BudgetCircuit(threshold=3)
        circuit.record(over_budget=True)
        circuit.record(over_budget=True)
        circuit.record(over_budget=False)  # resets
        assert circuit.consecutive_over == 0
        assert circuit.is_open is False

    def test_reset_method(self):
        circuit = BudgetCircuit(threshold=2)
        circuit.record(over_budget=True)
        circuit.record(over_budget=True)
        assert circuit.is_open is True
        circuit.reset()
        assert circuit.is_open is False
        assert circuit.consecutive_over == 0
