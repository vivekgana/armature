"""Circuit breaker for self-healing pipeline.

Pattern: CLOSED -> OPEN after N consecutive failures.
When open, the healer stops retrying and escalates to human.

From OpenAI: 'When something failed, the fix was almost never try harder...
human engineers always asked: what capability is missing?'
"""

from __future__ import annotations

from dataclasses import dataclass, field

from armature._internal.types import CircuitState


@dataclass
class CircuitBreaker:
    """Circuit breaker that opens after consecutive failures."""
    threshold: int = 3
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    history: list[dict[str, object]] = field(default_factory=list)

    def record_failure(self, details: str) -> None:
        """Record a failure attempt."""
        self.failure_count += 1
        self.history.append({"attempt": self.failure_count, "details": details, "fixed": False})
        if self.failure_count >= self.threshold:
            self.state = CircuitState.OPEN

    def record_success(self, details: str = "") -> None:
        """Record a successful fix."""
        self.history.append({"attempt": self.failure_count + 1, "details": details, "fixed": True})
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Whether the circuit breaker is open (stop retrying)."""
        return self.state == CircuitState.OPEN

    def reset(self) -> None:
        """Reset to closed state (for HALF_OPEN testing)."""
        self.state = CircuitState.HALF_OPEN
        self.failure_count = 0
