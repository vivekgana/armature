"""SWE-bench quality-correctness correlation analysis.

Pure-Python statistical functions (no numpy/scipy dependency).
Computes Pearson/Spearman correlation, ROC-AUC, and optimal F1 threshold
between Armature quality scores and task pass/fail outcomes.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from armature._internal.types import BenchmarkTaskResult, CorrelationResult


class QualityCorrelation:
    """Analyze correlation between Armature quality scores and task outcomes."""

    def __init__(self, task_results: list[BenchmarkTaskResult]) -> None:
        self.task_results = task_results

    def compute(self) -> CorrelationResult:
        """Run full correlation analysis."""
        if len(self.task_results) < 3:
            return CorrelationResult(
                pearson_r=0.0, spearman_rho=0.0, p_value=1.0,
                roc_auc=0.5, optimal_threshold=0.0,
                per_check_importance={}, quality_bands=[],
            )

        scores = [r.quality_score for r in self.task_results]
        outcomes = [1.0 if r.passed else 0.0 for r in self.task_results]

        pearson_r = _pearson(scores, outcomes)
        spearman_rho = _spearman(scores, outcomes)
        p_value = _pearson_p_value(pearson_r, len(scores))
        roc_auc = _compute_roc_auc(scores, outcomes)
        optimal_threshold = _find_optimal_f1_threshold(scores, outcomes)
        per_check = _compute_check_importance(self.task_results)
        bands = _compute_quality_bands(scores, outcomes)

        return CorrelationResult(
            pearson_r=round(pearson_r, 4),
            spearman_rho=round(spearman_rho, 4),
            p_value=round(p_value, 6),
            roc_auc=round(roc_auc, 4),
            optimal_threshold=round(optimal_threshold, 1),
            per_check_importance=per_check,
            quality_bands=bands,
        )


# ---------------------------------------------------------------------------
# Statistical functions (pure Python, no external dependencies)
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    mx, my = _mean(x), _mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))

    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _rank(values: list[float]) -> list[float]:
    """Assign ranks to values (average rank for ties)."""
    indexed = sorted(enumerate(values), key=lambda p: p[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


def _spearman(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation coefficient."""
    return _pearson(_rank(x), _rank(y))


def _pearson_p_value(r: float, n: int) -> float:
    """Approximate two-tailed p-value for Pearson r using t-distribution."""
    if n < 3 or abs(r) >= 1.0:
        return 0.0 if abs(r) >= 1.0 else 1.0

    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    # Approximate p-value using the normal distribution for large df
    if df > 30:
        return 2.0 * _normal_sf(abs(t_stat))
    # For small df, use a rough beta incomplete function approximation
    x = df / (df + t_stat * t_stat)
    p = _regularized_beta(x, df / 2.0, 0.5)
    return min(1.0, p)


def _normal_sf(z: float) -> float:
    """Survival function of standard normal (1 - CDF), Abramowitz & Stegun approx."""
    if z < 0:
        return 1.0 - _normal_sf(-z)
    t = 1.0 / (1.0 + 0.2316419 * z)
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
           t * (-1.821255978 + t * 1.330274429))))
    return poly * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _regularized_beta(x: float, a: float, b: float, max_iter: int = 200) -> float:
    """Regularized incomplete beta function via continued fraction (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    prefix = math.exp(
        a * math.log(x) + b * math.log(1 - x)
        - math.log(a)
        - _log_beta(a, b)
    )

    # Continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d

    for m in range(1, max_iter + 1):
        # Even step
        num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        f *= c * d

        # Odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = c * d
        f *= delta

        if abs(delta - 1.0) < 1e-10:
            break

    return prefix * f


def _log_beta(a: float, b: float) -> float:
    """Log of Beta function: log(B(a,b)) = lgamma(a) + lgamma(b) - lgamma(a+b)."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _compute_roc_auc(scores: list[float], labels: list[float]) -> float:
    """ROC AUC via trapezoidal integration on sorted thresholds."""
    if not scores or not labels:
        return 0.5

    n_pos = sum(1 for y in labels if y > 0.5)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Sort by score descending
    pairs = sorted(zip(scores, labels, strict=True), key=lambda p: -p[0])

    tp = 0
    fp = 0
    auc = 0.0
    prev_fpr = 0.0
    prev_tpr = 0.0

    for _score, label in pairs:
        if label > 0.5:
            tp += 1
        else:
            fp += 1

        tpr = tp / n_pos
        fpr = fp / n_neg

        # Trapezoid
        auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_fpr = fpr
        prev_tpr = tpr

    return auc


def _find_optimal_f1_threshold(scores: list[float], labels: list[float]) -> float:
    """Find quality score threshold that maximizes F1 score."""
    if not scores:
        return 0.0

    thresholds = sorted(set(scores))
    best_f1 = 0.0
    best_threshold = 0.0

    for threshold in thresholds:
        predictions = [1.0 if s >= threshold else 0.0 for s in scores]

        tp = sum(1 for p, y in zip(predictions, labels, strict=True) if p == 1 and y > 0.5)
        fp = sum(1 for p, y in zip(predictions, labels, strict=True) if p == 1 and y <= 0.5)
        fn = sum(1 for p, y in zip(predictions, labels, strict=True) if p == 0 and y > 0.5)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    return best_threshold


def _compute_check_importance(task_results: list[BenchmarkTaskResult]) -> dict[str, float]:
    """Compute per-check correlation with pass/fail (point-biserial)."""
    check_scores: dict[str, list[float]] = defaultdict(list)
    outcomes: list[float] = []

    for result in task_results:
        outcomes.append(1.0 if result.passed else 0.0)
        for check in result.check_results:
            check_scores[check.name].append(check.score)

    importance: dict[str, float] = {}
    for check_name, scores in check_scores.items():
        if len(scores) == len(outcomes) and len(scores) >= 3:
            r = abs(_pearson(scores, outcomes))
            importance[check_name] = round(r, 3)

    return dict(sorted(importance.items(), key=lambda kv: -kv[1]))


def _compute_quality_bands(
    scores: list[float],
    outcomes: list[float],
) -> list[dict[str, Any]]:
    """Group scores into quality bands and compute pass rates."""
    bands_def = [
        ("95-100", 95.0, 100.0),
        ("85-95", 85.0, 95.0),
        ("70-85", 70.0, 85.0),
        ("<70", 0.0, 70.0),
    ]

    bands: list[dict[str, Any]] = []
    for label, lo, hi in bands_def:
        in_band = [
            (s, o) for s, o in zip(scores, outcomes, strict=True)
            if lo <= s < hi or (hi == 100.0 and s == 100.0)
        ]
        n = len(in_band)
        if n == 0:
            bands.append({"band": label, "pass_rate": 0.0, "n": 0})
            continue

        pass_rate = sum(o for _, o in in_band) / n
        bands.append({"band": label, "pass_rate": round(pass_rate, 3), "n": n})

    return bands
