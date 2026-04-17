"""Tests for heal/circuit_breaker.py -- failure circuit breaker."""

from __future__ import annotations

import pytest

from armature._internal.types import CircuitState
from armature.heal.circuit_breaker import CircuitBreaker


class TestCircuitBreaker:
    """Tests for the self-heal circuit breaker."""

    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_open is False
        assert cb.failure_count == 0

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("error 1")
        cb.record_failure("error 2")
        assert cb.is_open is False
        cb.record_failure("error 3")
        assert cb.is_open is True
        assert cb.state == CircuitState.OPEN

    def test_success_resets(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("error 1")
        cb.record_failure("error 2")
        cb.record_success("fixed")
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_history_tracks_attempts(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure("error 1")
        cb.record_success("fixed")
        assert len(cb.history) == 2
        assert cb.history[0]["fixed"] is False
        assert cb.history[1]["fixed"] is True

    def test_reset_to_half_open(self):
        cb = CircuitBreaker(threshold=2)
        cb.record_failure("e1")
        cb.record_failure("e2")
        assert cb.is_open is True
        cb.reset()
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_open is False

    def test_custom_threshold(self):
        cb = CircuitBreaker(threshold=1)
        cb.record_failure("error")
        assert cb.is_open is True
