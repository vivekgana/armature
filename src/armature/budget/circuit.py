"""Budget circuit breaker -- pauses development when spending exceeds limits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetCircuit:
    """Circuit breaker for budget overruns.

    Opens when N consecutive tasks exceed their per-task budget,
    signaling the agent to pause and ask for human guidance.
    """
    threshold: int = 3
    consecutive_over: int = 0
    _open: bool = False

    def record(self, over_budget: bool) -> None:
        """Record whether a task was over budget."""
        if over_budget:
            self.consecutive_over += 1
            if self.consecutive_over >= self.threshold:
                self._open = True
        else:
            self.consecutive_over = 0

    @property
    def is_open(self) -> bool:
        """Whether the budget circuit breaker is open."""
        return self._open

    def reset(self) -> None:
        """Reset the circuit breaker after human review."""
        self._open = False
        self.consecutive_over = 0
