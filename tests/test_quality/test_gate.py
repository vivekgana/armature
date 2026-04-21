"""Tests for quality/gate.py -- quality gate evaluation."""

from __future__ import annotations

from armature._internal.types import QualityLevel
from armature.quality.gate import QualityGate, evaluate_quality_level


class TestQualityGate:
    """Tests for QualityGate dataclass."""

    def test_passes_above_threshold(self):
        gate = QualityGate(name="merge_ready", threshold=0.95)
        assert gate.passes(0.96) is True

    def test_fails_below_threshold(self):
        gate = QualityGate(name="merge_ready", threshold=0.95)
        assert gate.passes(0.90) is False

    def test_passes_at_threshold(self):
        gate = QualityGate(name="merge_ready", threshold=0.95)
        assert gate.passes(0.95) is True


class TestEvaluateQualityLevel:
    """Tests for evaluate_quality_level()."""

    def test_merge_ready(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.96, gates) == QualityLevel.MERGE_READY

    def test_review_ready(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.90, gates) == QualityLevel.REVIEW_READY

    def test_draft(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.75, gates) == QualityLevel.DRAFT

    def test_below_draft(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.50, gates) == QualityLevel.DRAFT

    def test_boundary_merge(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.95, gates) == QualityLevel.MERGE_READY

    def test_boundary_review(self):
        gates = {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95}
        assert evaluate_quality_level(0.85, gates) == QualityLevel.REVIEW_READY
