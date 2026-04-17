"""Quality gate thresholds and evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from armature._internal.types import QualityLevel


@dataclass
class QualityGate:
    """A quality gate with a threshold score."""
    name: str
    threshold: float

    def passes(self, score: float) -> bool:
        return score >= self.threshold


def evaluate_quality_level(score: float, gates: dict[str, float]) -> QualityLevel:
    """Determine which quality level a score achieves."""
    if score >= gates.get("merge_ready", 0.95):
        return QualityLevel.MERGE_READY
    if score >= gates.get("review_ready", 0.85):
        return QualityLevel.REVIEW_READY
    return QualityLevel.DRAFT
