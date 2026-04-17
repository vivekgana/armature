"""Tests for budget/reporter.py -- cost reporting and anomaly detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.budget.reporter import detect_anomalies
from armature.budget.tracker import SessionTracker
from armature.config.schema import BudgetConfig


@pytest.fixture
def tracker(tmp_path: Path) -> SessionTracker:
    config = BudgetConfig(enabled=True, storage=".armature/budget/")
    return SessionTracker(config, tmp_path)


class TestDetectAnomalies:
    """Tests for detect_anomalies() cost anomaly detection."""

    def test_detects_outlier(self, tracker: SessionTracker):
        # Normal costs
        for _ in range(5):
            tracker.log("SPEC-001", "build", 10000, 0.10, intent="code_gen")
        # Outlier
        tracker.log("SPEC-001", "build", 10000, 10.0, intent="code_gen")

        anomalies = detect_anomalies(tracker, "SPEC-001", threshold=3.0)
        assert len(anomalies) >= 1
        assert any("code_gen" in a for a in anomalies)

    def test_no_anomalies_for_uniform_costs(self, tracker: SessionTracker):
        for _ in range(5):
            tracker.log("SPEC-001", "build", 10000, 0.50, intent="code_gen")

        anomalies = detect_anomalies(tracker, "SPEC-001", threshold=3.0)
        assert len(anomalies) == 0

    def test_skips_single_request_intents(self, tracker: SessionTracker):
        tracker.log("SPEC-001", "build", 10000, 100.0, intent="code_gen")
        anomalies = detect_anomalies(tracker, "SPEC-001", threshold=3.0)
        assert len(anomalies) == 0  # need at least 2 requests
