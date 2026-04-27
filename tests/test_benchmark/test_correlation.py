"""Tests for benchmark/correlation.py -- statistical analysis."""

from __future__ import annotations

from armature._internal.types import BenchmarkTaskResult, CheckResult
from armature.benchmark.correlation import (
    QualityCorrelation,
    _compute_quality_bands,
    _compute_roc_auc,
    _find_optimal_f1_threshold,
    _mean,
    _pearson,
    _rank,
    _spearman,
)


def _make_result(quality: float, passed: bool, checks: list[CheckResult] | None = None) -> BenchmarkTaskResult:
    return BenchmarkTaskResult(
        task_id=f"T-{quality:.0f}",
        agent="test",
        quality_score=quality,
        budget_tokens=10000,
        budget_cost_usd=0.20,
        heal_attempts=0,
        heal_fixed=0,
        cache_hits=0,
        cache_total=0,
        duration_seconds=1.0,
        passed=passed,
        check_results=checks or [],
    )


class TestPearson:
    """Tests for Pearson correlation."""

    def test_perfect_positive(self):
        r = _pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert abs(r - 1.0) < 1e-10

    def test_perfect_negative(self):
        r = _pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert abs(r - (-1.0)) < 1e-10

    def test_no_correlation(self):
        r = _pearson([1, 2, 3, 4, 5], [3, 1, 4, 1, 5])
        assert abs(r) < 0.5

    def test_constant_returns_zero(self):
        r = _pearson([5, 5, 5], [1, 2, 3])
        assert r == 0.0

    def test_single_element(self):
        r = _pearson([1], [1])
        assert r == 0.0

    def test_empty(self):
        r = _pearson([], [])
        assert r == 0.0


class TestSpearman:
    """Tests for Spearman rank correlation."""

    def test_perfect_monotonic(self):
        rho = _spearman([10, 20, 30, 40, 50], [2, 4, 6, 8, 10])
        assert abs(rho - 1.0) < 1e-10

    def test_perfect_inverse_monotonic(self):
        rho = _spearman([10, 20, 30, 40, 50], [10, 8, 6, 4, 2])
        assert abs(rho - (-1.0)) < 1e-10

    def test_rank_with_ties(self):
        ranks = _rank([10, 20, 20, 30])
        assert ranks[0] == 1.0
        assert ranks[1] == 2.5
        assert ranks[2] == 2.5
        assert ranks[3] == 4.0


class TestROCAUC:
    """Tests for ROC AUC computation."""

    def test_perfect_classifier(self):
        scores = [90, 80, 70, 60, 50, 40, 30, 20, 10, 5]
        labels = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        auc = _compute_roc_auc(scores, labels)
        assert auc == 1.0

    def test_worst_classifier(self):
        scores = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
        labels = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        auc = _compute_roc_auc(scores, labels)
        assert auc == 0.0

    def test_random_classifier(self):
        scores = [50, 50, 50, 50, 50, 50, 50, 50]
        labels = [1, 0, 1, 0, 1, 0, 1, 0]
        auc = _compute_roc_auc(scores, labels)
        assert 0.3 <= auc <= 0.7

    def test_empty_returns_half(self):
        assert _compute_roc_auc([], []) == 0.5

    def test_all_positive_returns_half(self):
        assert _compute_roc_auc([90, 80, 70], [1, 1, 1]) == 0.5

    def test_all_negative_returns_half(self):
        assert _compute_roc_auc([90, 80, 70], [0, 0, 0]) == 0.5


class TestOptimalF1:
    """Tests for F1-optimal threshold search."""

    def test_clear_separation(self):
        scores = [95, 90, 85, 80, 40, 30, 20, 10]
        labels = [1, 1, 1, 1, 0, 0, 0, 0]
        threshold = _find_optimal_f1_threshold(scores, labels)
        assert 40 <= threshold <= 95

    def test_empty_scores(self):
        assert _find_optimal_f1_threshold([], []) == 0.0


class TestQualityBands:
    """Tests for quality band computation."""

    def test_all_bands_populated(self):
        scores = [97, 92, 88, 80, 65, 50]
        outcomes = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
        bands = _compute_quality_bands(scores, outcomes)
        assert len(bands) == 4
        band_names = [b["band"] for b in bands]
        assert band_names == ["95-100", "85-95", "70-85", "<70"]

    def test_high_band_high_pass_rate(self):
        scores = [96, 97, 98, 99, 100]
        outcomes = [1.0, 1.0, 1.0, 1.0, 1.0]
        bands = _compute_quality_bands(scores, outcomes)
        top = next(b for b in bands if b["band"] == "95-100")
        assert top["pass_rate"] == 1.0
        assert top["n"] == 5

    def test_monotonic_pass_rate(self):
        scores = [97, 90, 80, 60, 96, 88, 75, 50]
        outcomes = [1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0]
        bands = _compute_quality_bands(scores, outcomes)
        top = next(b for b in bands if b["band"] == "95-100")
        low = next(b for b in bands if b["band"] == "<70")
        assert top["pass_rate"] >= low["pass_rate"]


class TestQualityCorrelation:
    """Integration tests for QualityCorrelation.compute()."""

    def test_too_few_results(self):
        results = [_make_result(90.0, True), _make_result(80.0, False)]
        corr = QualityCorrelation(results)
        r = corr.compute()
        assert r.pearson_r == 0.0
        assert r.p_value == 1.0
        assert r.roc_auc == 0.5

    def test_strong_positive_correlation(self):
        results = [
            _make_result(98, True), _make_result(95, True),
            _make_result(90, True), _make_result(85, True),
            _make_result(80, True), _make_result(70, False),
            _make_result(60, False), _make_result(50, False),
            _make_result(40, False), _make_result(30, False),
        ]
        corr = QualityCorrelation(results)
        r = corr.compute()
        assert r.pearson_r > 0.7
        assert r.spearman_rho > 0.7
        assert r.roc_auc > 0.8

    def test_with_check_results(self):
        checks = [
            CheckResult(name="lint", passed=True, score=0.9, weight=25),
            CheckResult(name="test", passed=True, score=0.8, weight=25),
        ]
        results = [
            _make_result(90, True, checks),
            _make_result(80, True, checks),
            _make_result(50, False, checks),
            _make_result(40, False, checks),
        ]
        corr = QualityCorrelation(results)
        r = corr.compute()
        assert isinstance(r.per_check_importance, dict)
        assert isinstance(r.quality_bands, list)
        assert len(r.quality_bands) == 4

    def test_result_fields_are_numeric(self):
        results = [
            _make_result(95, True), _make_result(85, True),
            _make_result(75, False), _make_result(55, False),
        ]
        r = QualityCorrelation(results).compute()
        assert isinstance(r.pearson_r, (int, float))
        assert isinstance(r.spearman_rho, (int, float))
        assert isinstance(r.roc_auc, (int, float))
        assert isinstance(r.optimal_threshold, (int, float))


class TestMean:
    def test_basic(self):
        assert _mean([1, 2, 3]) == 2.0

    def test_empty(self):
        assert _mean([]) == 0.0
