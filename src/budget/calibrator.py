"""Auto-calibration of budget multipliers from historical actuals.

After each spec completes, compares actual token usage against benchmark
predictions and updates adjustment multipliers using exponential moving
average (EMA). Three calibration axes:

1. Historical: actual/predicted ratio per task type
2. Model verbosity: output token ratio per model vs Sonnet baseline
3. Cache hit rate: observed prompt cache hit rate for the project

Also includes industry benchmark targets derived from:
- SWE-bench (Jimenez et al., 2024): real-world GitHub issue resolution
- DevBench (Li et al., 2024): full SDLC coverage (req -> design -> code -> test)
- AgentBench (Liu et al., 2024): multi-environment agent evaluation
- HumanEval+ / MHPP (Liu et al., 2024): multi-language code generation
- RepoBench (Liu et al., 2023): repository-level code completion

Confidence ramps from 0.0 (no data) to 0.95 (10+ specs), controlling
how much weight calibrated values get vs hardcoded defaults.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from armature.budget.benchmark import BudgetBenchmark
from armature.budget.tracker import SessionTracker


# EMA decay factor: 0.3 means 30% weight on newest spec, 70% on accumulated
EMA_ALPHA = 0.3


def _find_benchmarks_file() -> Path | None:
    """Find industry_benchmarks.yaml: project root first, then package defaults."""
    cwd = Path.cwd()
    for candidate in [
        cwd / "industry_benchmarks.yaml",
        cwd / "data" / "industry_benchmarks.yaml",
        cwd / ".armature" / "industry_benchmarks.yaml",
    ]:
        if candidate.exists():
            return candidate
    pkg_default = Path(__file__).parent.parent.parent / "data" / "industry_benchmarks.yaml"
    if pkg_default.exists():
        return pkg_default
    return None


def load_industry_benchmarks() -> dict:
    """Load industry benchmarks from YAML file.

    Search order:
      1. ./industry_benchmarks.yaml  (project root override)
      2. ./data/industry_benchmarks.yaml
      3. ./.armature/industry_benchmarks.yaml
      4. Package default (data/industry_benchmarks.yaml shipped with armature)

    Returns raw dict from YAML, or empty dict if no file found.
    """
    path = _find_benchmarks_file()
    if path is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

# Default model verbosity multipliers (before calibration)
DEFAULT_MODEL_VERBOSITY: dict[str, float] = {
    "claude-opus": 1.4,
    "claude-sonnet": 1.0,
    "claude-haiku": 0.7,
    "gpt-4o": 1.1,
    "gpt-4o-mini": 0.8,
    "gemini-2.5-pro": 1.1,
    "gemini-2.5-flash": 0.85,
    "gemini-flash-lite": 0.7,
    "sonar-pro": 1.0,
    "sonar": 0.75,
}

# Default task adjustment (1.0 = predictions are accurate)
DEFAULT_TASK_ADJUSTMENT = 1.0


# ---------------------------------------------------------------------------
# Industry benchmark targets
# Loaded from external YAML (data/industry_benchmarks.yaml) for shareability.
# Hardcoded defaults are used as fallbacks if no YAML file is found.
# ---------------------------------------------------------------------------

_BENCHMARKS_DATA: dict = {}


def _get_benchmarks() -> dict:
    """Lazy-load benchmarks on first access."""
    global _BENCHMARKS_DATA
    if not _BENCHMARKS_DATA:
        _BENCHMARKS_DATA = load_industry_benchmarks()
    return _BENCHMARKS_DATA


@dataclass(frozen=True)
class PhaseTokenTarget:
    """Industry benchmark: tokens per LOC for an SDLC phase."""
    read_tokens_per_loc: float
    write_tokens_per_loc: float
    source: str


_DEFAULT_PHASE_TARGETS = {
    "validate": {"read_tokens_per_loc": 3.5, "write_tokens_per_loc": 2.0, "source": "DevBench (Li et al., 2024)"},
    "audit":    {"read_tokens_per_loc": 7.5, "write_tokens_per_loc": 5.5, "source": "DevBench (Li et al., 2024)"},
    "plan":     {"read_tokens_per_loc": 7.5, "write_tokens_per_loc": 5.5, "source": "DevBench (Li et al., 2024)"},
    "build":    {"read_tokens_per_loc": 15.0, "write_tokens_per_loc": 10.0, "source": "SWE-bench (Jimenez et al., 2024)"},
    "test":     {"read_tokens_per_loc": 11.5, "write_tokens_per_loc": 14.0, "source": "HumanEval+ (Liu et al., 2024)"},
    "review":   {"read_tokens_per_loc": 20.0, "write_tokens_per_loc": 2.0, "source": "Industry consensus"},
}

_DEFAULT_TASK_TARGETS = {
    "bugfix":   {"p25": 15_000, "median": 30_000, "p75": 60_000},
    "feature":  {"p25": 50_000, "median": 120_000, "p75": 250_000},
    "refactor": {"p25": 25_000, "median": 60_000, "p75": 150_000},
    "spike":    {"p25": 5_000,  "median": 15_000, "p75": 40_000},
    "test":     {"p25": 20_000, "median": 50_000, "p75": 120_000},
}

_DEFAULT_LANGUAGE_BENCHMARKS = {
    "python":     {"easy": 2_500, "medium": 8_000, "hard": 15_000},
    "typescript": {"easy": 3_000, "medium": 9_500, "hard": 18_000},
    "go":         {"easy": 2_200, "medium": 7_000, "hard": 12_000},
    "rust":       {"easy": 2_200, "medium": 7_500, "hard": 12_000},
}

_DEFAULT_QUALITY_CURVE = [
    (10_000, 0.40), (25_000, 0.55), (50_000, 0.70), (100_000, 0.82),
    (200_000, 0.90), (500_000, 0.94), (1_000_000, 0.96), (2_000_000, 0.97),
]


def _build_phase_targets() -> dict[str, PhaseTokenTarget]:
    data = _get_benchmarks().get("phase_targets", _DEFAULT_PHASE_TARGETS)
    return {
        name: PhaseTokenTarget(
            read_tokens_per_loc=v.get("read_tokens_per_loc", 10.0),
            write_tokens_per_loc=v.get("write_tokens_per_loc", 5.0),
            source=v.get("source", "custom"),
        )
        for name, v in data.items()
    }


def _build_task_targets() -> dict[str, dict[str, int]]:
    return _get_benchmarks().get("task_targets", _DEFAULT_TASK_TARGETS)


def _build_language_benchmarks() -> dict[str, dict[str, int]]:
    return _get_benchmarks().get("language_benchmarks", _DEFAULT_LANGUAGE_BENCHMARKS)


def _build_quality_curve() -> list[tuple[int, float]]:
    raw = _get_benchmarks().get("quality_budget_curve")
    if raw is None:
        return _DEFAULT_QUALITY_CURVE
    return [(entry["tokens"], entry["quality_pct"]) for entry in raw]


# Public module-level accessors (lazy-loaded from YAML)
INDUSTRY_PHASE_TARGETS: dict[str, PhaseTokenTarget] = {}
INDUSTRY_TASK_TARGETS: dict[str, dict[str, int]] = {}
INDUSTRY_LANGUAGE_BENCHMARKS: dict[str, dict[str, int]] = {}
QUALITY_BUDGET_CURVE: list[tuple[int, float]] = []


def _ensure_loaded() -> None:
    """Populate module-level dicts on first use."""
    global INDUSTRY_PHASE_TARGETS, INDUSTRY_TASK_TARGETS
    global INDUSTRY_LANGUAGE_BENCHMARKS, QUALITY_BUDGET_CURVE
    if not INDUSTRY_PHASE_TARGETS:
        INDUSTRY_PHASE_TARGETS.update(_build_phase_targets())
        INDUSTRY_TASK_TARGETS.update(_build_task_targets())
        INDUSTRY_LANGUAGE_BENCHMARKS.update(_build_language_benchmarks())
        QUALITY_BUDGET_CURVE.extend(_build_quality_curve())


_ensure_loaded()


# Cost-efficiency metric targets
@dataclass(frozen=True)
class EfficiencyTargets:
    """Industry targets for cost-efficiency metrics."""
    target_cost_per_loc_standard: float = 0.01
    target_cost_per_loc_premium: float = 0.05
    target_cache_hit_rate: float = 0.40
    target_routing_savings_ratio: float = 2.0
    target_calibration_drift: float = 0.20
    target_tokens_per_bugfix: int = 30_000
    target_tokens_per_feature: int = 120_000


def _build_efficiency_targets() -> EfficiencyTargets:
    raw = _get_benchmarks().get("efficiency_targets")
    if raw is None:
        return EfficiencyTargets()
    return EfficiencyTargets(
        target_cost_per_loc_standard=raw.get("cost_per_loc_standard", 0.01),
        target_cost_per_loc_premium=raw.get("cost_per_loc_premium", 0.05),
        target_cache_hit_rate=raw.get("cache_hit_rate", 0.40),
        target_routing_savings_ratio=raw.get("routing_savings_ratio", 2.0),
        target_calibration_drift=raw.get("calibration_drift", 0.20),
        target_tokens_per_bugfix=raw.get("tokens_per_bugfix", 30_000),
        target_tokens_per_feature=raw.get("tokens_per_feature", 120_000),
    )


EFFICIENCY_TARGETS = _build_efficiency_targets()


@dataclass
class IndustryComparison:
    """Result of comparing project actuals against industry benchmarks."""
    # Per-task-type: where does this project's actual sit vs industry percentiles?
    task_positions: dict[str, dict]   # task_type -> {actual, p25, median, p75, percentile_label}
    # Quality-budget position
    budget_tokens: int
    estimated_quality_pct: float
    quality_ceiling_note: str
    # Cost-efficiency metrics
    cost_per_loc: float | None
    cache_hit_rate: float
    routing_savings_ratio: float | None
    calibration_drift: float | None
    # Phase allocation vs DevBench
    phase_comparison: dict[str, dict]   # phase -> {actual_pct, industry_pct, deviation}
    # Efficiency grades
    grades: dict[str, str]             # metric -> "A" / "B" / "C" / "D"


@dataclass
class CalibrationProfile:
    """All adjustable multipliers, learned from historical data."""
    task_adjustments: dict[str, float] = field(default_factory=dict)
    model_verbosity: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_MODEL_VERBOSITY)
    )
    cache_hit_rate: float = 0.0
    specs_calibrated: int = 0
    last_calibrated: str = ""
    confidence: float = 0.0


class CalibrationStore:
    """Load/save calibration profile to .armature/calibration.json."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.profile_path = storage_dir / "calibration.json"

    def load(self) -> CalibrationProfile:
        """Load the calibration profile, or return defaults if none exists."""
        if not self.profile_path.exists():
            return CalibrationProfile()
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            return CalibrationProfile(
                task_adjustments=data.get("task_adjustments", {}),
                model_verbosity=data.get("model_verbosity", dict(DEFAULT_MODEL_VERBOSITY)),
                cache_hit_rate=data.get("cache_hit_rate", 0.0),
                specs_calibrated=data.get("specs_calibrated", 0),
                last_calibrated=data.get("last_calibrated", ""),
                confidence=data.get("confidence", 0.0),
            )
        except (json.JSONDecodeError, OSError):
            return CalibrationProfile()

    def save(self, profile: CalibrationProfile) -> None:
        """Persist the calibration profile."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(
            json.dumps(asdict(profile), indent=2), encoding="utf-8"
        )


def calibrate_from_spec(
    spec_id: str,
    tracker: SessionTracker,
    benchmark: BudgetBenchmark,
    store: CalibrationStore,
) -> CalibrationProfile:
    """Compare one spec's actuals vs predictions, update profile with EMA.

    Steps:
    1. Load existing profile
    2. Get actual usage from tracker
    3. Compare against benchmark predictions
    4. Update task adjustments with EMA
    5. Update model verbosity from actual output ratios
    6. Update cache hit rate from observed cache hits
    7. Recalculate confidence
    8. Save and return updated profile
    """
    profile = store.load()
    usage = tracker.get_usage(spec_id)

    if usage["requests"] == 0:
        return profile

    # --- 1. Historical calibration: actual/predicted per task type ---
    # Map spec phases to task types for comparison
    phase_to_task_type = {
        "build": "feature",
        "test": "test",
        "validate": "spike",
        "audit": "spike",
        "review": "spike",
    }

    for phase, phase_data in usage.get("phases", {}).items():
        task_type = phase_to_task_type.get(phase, "feature")
        benchmark_est = benchmark.estimates.get(task_type)
        if benchmark_est is None or benchmark_est.estimated_tokens == 0:
            continue

        actual_tokens = phase_data.get("tokens", 0)
        predicted_tokens = benchmark_est.estimated_tokens
        if predicted_tokens == 0:
            continue

        ratio = actual_tokens / predicted_tokens
        # Clamp ratio to prevent extreme outliers from skewing calibration
        ratio = max(0.2, min(5.0, ratio))

        prev = profile.task_adjustments.get(task_type, DEFAULT_TASK_ADJUSTMENT)
        updated = _ema_update(prev, ratio)
        profile.task_adjustments[task_type] = round(updated, 3)

    # --- 2. Model verbosity: output ratio per model ---
    intent_usage = tracker.get_usage_by_intent(spec_id)
    provider_usage = tracker.get_usage_by_provider(spec_id)

    # Aggregate per-model input/output tokens from JSONL entries
    entries = tracker._load_entries(spec_id)
    model_io: dict[str, dict[str, int]] = {}  # model -> {input, output}
    for entry in entries:
        m = entry.get("model", "")
        if not m:
            continue
        inp = entry.get("input_tokens", 0)
        out = entry.get("output_tokens", 0)
        if inp <= 0 or out <= 0:
            continue
        if m not in model_io:
            model_io[m] = {"input": 0, "output": 0}
        model_io[m]["input"] += inp
        model_io[m]["output"] += out

    # Compute output/input ratio per model and EMA-update verbosity
    sonnet_default = DEFAULT_MODEL_VERBOSITY.get("claude-sonnet", 1.0)
    for m, io in model_io.items():
        if io["input"] == 0:
            continue
        observed_ratio = io["output"] / io["input"]
        # Normalize to Sonnet baseline (Sonnet output/input ratio ~ 0.4)
        baseline_ratio = 0.4
        observed_verbosity = observed_ratio / baseline_ratio * sonnet_default
        observed_verbosity = max(0.3, min(3.0, observed_verbosity))

        prev_verbosity = profile.model_verbosity.get(
            m, DEFAULT_MODEL_VERBOSITY.get(m, 1.0)
        )
        profile.model_verbosity[m] = round(
            _ema_update(prev_verbosity, observed_verbosity), 3
        )

    # --- 3. Cache hit rate from observed cache hits ---
    cache_stats = tracker.get_semantic_cache_stats(spec_id)
    if cache_stats["total_requests"] > 0:
        observed_rate = cache_stats["hit_rate"]
        prev_rate = profile.cache_hit_rate
        profile.cache_hit_rate = round(_ema_update(prev_rate, observed_rate), 3)

    # --- 4. Update metadata ---
    profile.specs_calibrated += 1
    profile.last_calibrated = datetime.now(timezone.utc).isoformat()
    profile.confidence = _calculate_confidence(profile.specs_calibrated)

    # --- 5. Persist ---
    store.save(profile)
    return profile


def apply_calibration(
    profile: CalibrationProfile,
    config_overrides: dict | None = None,
    min_confidence: float = 0.0,
) -> dict:
    """Return effective multipliers: manual override > calibrated > hardcoded default.

    Returns a dict with:
    - task_adjustments: dict[str, float] -- per task type
    - model_verbosity: dict[str, float] -- per model
    - cache_hit_rate: float
    - confidence: float
    """
    overrides = config_overrides or {}

    # Task adjustments
    effective_tasks: dict[str, float] = {}
    for task_type in ("bugfix", "feature", "refactor", "spike", "test"):
        # Check manual override first
        override_val = overrides.get("task_overrides", {}).get(task_type)
        if override_val is not None:
            effective_tasks[task_type] = override_val
        elif profile.confidence >= min_confidence and task_type in profile.task_adjustments:
            # Blend calibrated with default based on confidence
            calibrated = profile.task_adjustments[task_type]
            default = DEFAULT_TASK_ADJUSTMENT
            effective_tasks[task_type] = _blend(calibrated, default, profile.confidence)
        else:
            effective_tasks[task_type] = DEFAULT_TASK_ADJUSTMENT

    # Model verbosity
    effective_models: dict[str, float] = {}
    for model, default_mult in DEFAULT_MODEL_VERBOSITY.items():
        override_val = overrides.get("model_verbosity_overrides", {}).get(model)
        if override_val is not None:
            effective_models[model] = override_val
        elif profile.confidence >= min_confidence and model in profile.model_verbosity:
            calibrated = profile.model_verbosity[model]
            effective_models[model] = _blend(calibrated, default_mult, profile.confidence)
        else:
            effective_models[model] = default_mult

    # Cache hit rate
    cache_override = overrides.get("cache_hit_rate_override")
    if cache_override is not None:
        effective_cache = cache_override
    elif profile.confidence >= min_confidence:
        effective_cache = profile.cache_hit_rate
    else:
        effective_cache = 0.0

    return {
        "task_adjustments": effective_tasks,
        "model_verbosity": effective_models,
        "cache_hit_rate": effective_cache,
        "confidence": profile.confidence,
    }


def _ema_update(previous: float, new_value: float) -> float:
    """Exponential moving average update."""
    return EMA_ALPHA * new_value + (1 - EMA_ALPHA) * previous


def _blend(calibrated: float, default: float, confidence: float) -> float:
    """Blend calibrated value with default based on confidence level."""
    return round(confidence * calibrated + (1 - confidence) * default, 3)


def compare_against_industry(
    benchmark: BudgetBenchmark,
    tracker: SessionTracker,
    spec_id: str,
    *,
    cost_per_loc: float | None = None,
    routing_savings_ratio: float | None = None,
) -> IndustryComparison:
    """Compare a spec's actuals against industry benchmark targets.

    Uses per-task-type industry percentiles (SWE-bench, DevBench),
    quality-budget curve (AgentBench), and cost-efficiency targets.

    Args:
        benchmark: Project benchmark from calculate_benchmark()
        tracker: Session tracker with actual usage data
        spec_id: Spec to compare
        cost_per_loc: Optional measured $/LOC (if available)
        routing_savings_ratio: Optional ratio of all-premium / routed cost
    """
    usage = tracker.get_usage(spec_id)
    cache_stats = tracker.get_semantic_cache_stats(spec_id)

    # --- Task-type positioning against industry percentiles ---
    task_positions: dict[str, dict] = {}
    for task_type, targets in INDUSTRY_TASK_TARGETS.items():
        est = benchmark.estimates.get(task_type)
        actual = est.estimated_tokens if est else 0
        # Use actual usage if available from phases
        phase_map = {"bugfix": "build", "feature": "build", "refactor": "build",
                     "spike": "validate", "test": "test"}
        mapped_phase = phase_map.get(task_type, "build")
        phase_data = usage.get("phases", {}).get(mapped_phase, {})
        if phase_data.get("tokens", 0) > 0:
            actual = phase_data["tokens"]

        # Determine percentile label
        p25, median, p75 = targets["p25"], targets["median"], targets["p75"]
        if actual <= p25:
            label = "<p25 (very efficient)"
        elif actual <= median:
            label = "p25-p50 (efficient)"
        elif actual <= p75:
            label = "p50-p75 (typical)"
        else:
            label = ">p75 (high usage)"

        task_positions[task_type] = {
            "actual": actual,
            "p25": p25,
            "median": median,
            "p75": p75,
            "percentile_label": label,
        }

    # --- Quality-budget position ---
    budget_tokens = usage.get("total_tokens", 0) or benchmark.recommended_tokens
    quality_pct, quality_note = assess_quality_budget_position(budget_tokens)

    # --- Phase allocation vs industry targets ---
    phase_comparison: dict[str, dict] = {}
    total_tokens = usage.get("total_tokens", 1)
    for phase, target in INDUSTRY_PHASE_TARGETS.items():
        phase_data = usage.get("phases", {}).get(phase, {})
        actual_tokens = phase_data.get("tokens", 0)
        actual_pct = (actual_tokens / total_tokens * 100) if total_tokens > 0 else 0
        # Industry % is based on the ratio of this phase's tokens/LOC to total
        total_industry = sum(t.read_tokens_per_loc + t.write_tokens_per_loc
                             for t in INDUSTRY_PHASE_TARGETS.values())
        industry_pct = ((target.read_tokens_per_loc + target.write_tokens_per_loc)
                        / total_industry * 100) if total_industry > 0 else 0
        phase_comparison[phase] = {
            "actual_pct": round(actual_pct, 1),
            "industry_pct": round(industry_pct, 1),
            "deviation": round(actual_pct - industry_pct, 1),
            "source": target.source,
        }

    # --- Calibration drift ---
    calibration_drift: float | None = None
    if usage.get("total_tokens", 0) > 0 and benchmark.recommended_tokens > 0:
        predicted = benchmark.estimates.get("feature", benchmark.estimates.get("bugfix"))
        if predicted and predicted.estimated_tokens > 0:
            # Drift = |actual - predicted| / predicted for the dominant task type
            actual_total = usage["total_tokens"]
            calibration_drift = abs(actual_total - predicted.estimated_tokens) / predicted.estimated_tokens

    comparison = IndustryComparison(
        task_positions=task_positions,
        budget_tokens=budget_tokens,
        estimated_quality_pct=quality_pct,
        quality_ceiling_note=quality_note,
        cost_per_loc=cost_per_loc,
        cache_hit_rate=cache_stats["hit_rate"],
        routing_savings_ratio=routing_savings_ratio,
        calibration_drift=calibration_drift,
        phase_comparison=phase_comparison,
        grades={},
    )
    comparison.grades = compute_efficiency_grades(comparison)
    return comparison


def assess_quality_budget_position(budget_tokens: int) -> tuple[float, str]:
    """Interpolate the quality-budget curve for a given token budget.

    Returns (estimated_quality_pct, ceiling_note).
    Based on AgentBench + SWE-bench performance-vs-cost analysis.
    """
    if budget_tokens <= 0:
        return 0.0, "No budget allocated"

    # Below minimum
    if budget_tokens <= QUALITY_BUDGET_CURVE[0][0]:
        return QUALITY_BUDGET_CURVE[0][1], "Below minimum viable budget"

    # Above maximum
    if budget_tokens >= QUALITY_BUDGET_CURVE[-1][0]:
        return QUALITY_BUDGET_CURVE[-1][1], "At ceiling -- additional tokens yield negligible quality gains"

    # Linear interpolation between curve points
    for i in range(len(QUALITY_BUDGET_CURVE) - 1):
        t1, q1 = QUALITY_BUDGET_CURVE[i]
        t2, q2 = QUALITY_BUDGET_CURVE[i + 1]
        if t1 <= budget_tokens <= t2:
            # Interpolate in log-space for tokens (smoother curve)
            log_t = math.log(budget_tokens)
            log_t1 = math.log(t1)
            log_t2 = math.log(t2)
            frac = (log_t - log_t1) / (log_t2 - log_t1)
            quality = q1 + frac * (q2 - q1)

            # Generate note based on position
            if quality < 0.60:
                note = "Limited context -- expect frequent gaps and retries"
            elif quality < 0.75:
                note = "Reasonable quality but some context limitations"
            elif quality < 0.85:
                note = "Good quality -- sufficient context for most tasks"
            elif quality < 0.92:
                note = "Diminishing returns zone -- marginal gains per additional token"
            else:
                note = "Near ceiling -- very marginal gains from additional budget"

            return round(quality, 3), note

    return QUALITY_BUDGET_CURVE[-1][1], "At ceiling"


def compute_efficiency_grades(comparison: IndustryComparison) -> dict[str, str]:
    """Assign A/B/C/D grades to efficiency metrics.

    Grading rubric:
      A = meets or exceeds industry target
      B = within 1.5x of target
      C = within 2.5x of target
      D = worse than 2.5x target
    """
    targets = EFFICIENCY_TARGETS
    grades: dict[str, str] = {}

    # Cache hit rate: higher is better
    if comparison.cache_hit_rate >= targets.target_cache_hit_rate:
        grades["cache_efficiency"] = "A"
    elif comparison.cache_hit_rate >= targets.target_cache_hit_rate * 0.6:
        grades["cache_efficiency"] = "B"
    elif comparison.cache_hit_rate >= targets.target_cache_hit_rate * 0.3:
        grades["cache_efficiency"] = "C"
    else:
        grades["cache_efficiency"] = "D"

    # Cost per LOC: lower is better
    if comparison.cost_per_loc is not None:
        threshold = targets.target_cost_per_loc_standard
        if comparison.cost_per_loc <= threshold:
            grades["cost_per_loc"] = "A"
        elif comparison.cost_per_loc <= threshold * 1.5:
            grades["cost_per_loc"] = "B"
        elif comparison.cost_per_loc <= threshold * 2.5:
            grades["cost_per_loc"] = "C"
        else:
            grades["cost_per_loc"] = "D"

    # Routing savings: higher ratio is better (routed cost < all-premium)
    if comparison.routing_savings_ratio is not None:
        target_ratio = targets.target_routing_savings_ratio
        if comparison.routing_savings_ratio >= target_ratio:
            grades["routing_savings"] = "A"
        elif comparison.routing_savings_ratio >= target_ratio * 0.7:
            grades["routing_savings"] = "B"
        elif comparison.routing_savings_ratio >= target_ratio * 0.4:
            grades["routing_savings"] = "C"
        else:
            grades["routing_savings"] = "D"

    # Calibration drift: lower is better
    if comparison.calibration_drift is not None:
        drift_target = targets.target_calibration_drift
        if comparison.calibration_drift <= drift_target:
            grades["calibration_accuracy"] = "A"
        elif comparison.calibration_drift <= drift_target * 1.5:
            grades["calibration_accuracy"] = "B"
        elif comparison.calibration_drift <= drift_target * 2.5:
            grades["calibration_accuracy"] = "C"
        else:
            grades["calibration_accuracy"] = "D"

    # Task-level grades: where does the project sit vs industry median?
    for task_type, pos in comparison.task_positions.items():
        if pos["actual"] <= 0:
            continue
        median = pos["median"]
        if pos["actual"] <= pos["p25"]:
            grades[f"task_{task_type}"] = "A"
        elif pos["actual"] <= median:
            grades[f"task_{task_type}"] = "B"
        elif pos["actual"] <= pos["p75"]:
            grades[f"task_{task_type}"] = "C"
        else:
            grades[f"task_{task_type}"] = "D"

    return grades


def format_industry_comparison(comparison: IndustryComparison) -> str:
    """Format an IndustryComparison as human-readable text."""
    lines: list[str] = []

    lines.append("INDUSTRY BENCHMARK COMPARISON")
    lines.append("=" * 50)

    # Task-type positioning
    lines.append("\n  Token Usage vs Industry Percentiles")
    lines.append(f"  {'Task':<12} {'Actual':>10} {'p25':>10} {'Median':>10} {'p75':>10}  Position")
    lines.append(f"  {'-' * 72}")
    for task_type in ["bugfix", "feature", "refactor", "spike", "test"]:
        pos = comparison.task_positions.get(task_type)
        if not pos:
            continue
        lines.append(
            f"  {task_type:<12} {pos['actual']:>10,} {pos['p25']:>10,} "
            f"{pos['median']:>10,} {pos['p75']:>10,}  {pos['percentile_label']}"
        )

    # Quality-budget position
    lines.append(f"\n  Quality-Budget Position")
    lines.append(f"  {'-' * 50}")
    lines.append(f"  Budget:           {comparison.budget_tokens:,} tokens")
    lines.append(f"  Expected quality: {comparison.estimated_quality_pct:.0%}")
    lines.append(f"  Note:             {comparison.quality_ceiling_note}")

    # Phase allocation
    lines.append(f"\n  Phase Allocation vs Industry (DevBench/SWE-bench)")
    lines.append(f"  {'Phase':<12} {'Actual%':>10} {'Industry%':>10} {'Delta':>10}  Source")
    lines.append(f"  {'-' * 65}")
    for phase in ["validate", "audit", "plan", "build", "test", "review"]:
        pc = comparison.phase_comparison.get(phase)
        if not pc:
            continue
        delta_str = f"{pc['deviation']:+.1f}%"
        lines.append(
            f"  {phase:<12} {pc['actual_pct']:>9.1f}% {pc['industry_pct']:>9.1f}% "
            f"{delta_str:>10}  {pc['source']}"
        )

    # Efficiency metrics
    lines.append(f"\n  Cost-Efficiency Metrics")
    lines.append(f"  {'-' * 50}")
    if comparison.cost_per_loc is not None:
        lines.append(f"  Cost/LOC:            ${comparison.cost_per_loc:.3f}")
    lines.append(f"  Cache hit rate:      {comparison.cache_hit_rate:.0%}")
    if comparison.routing_savings_ratio is not None:
        lines.append(f"  Routing savings:     {comparison.routing_savings_ratio:.1f}x")
    if comparison.calibration_drift is not None:
        lines.append(f"  Calibration drift:   {comparison.calibration_drift:.0%}")

    # Grades
    if comparison.grades:
        lines.append(f"\n  Efficiency Grades")
        lines.append(f"  {'-' * 50}")
        for metric, grade in sorted(comparison.grades.items()):
            label = metric.replace("_", " ").title()
            lines.append(f"  {label:<30} {grade}")

    return "\n".join(lines)


def _calculate_confidence(specs_calibrated: int) -> float:
    """Calculate confidence level from number of specs calibrated.

    Ramp: 0 specs -> 0.0, 3 -> 0.5, 5 -> 0.7, 10 -> 0.95
    Uses a logistic-like curve: confidence = 1 - e^(-0.25 * n)
    """
    if specs_calibrated <= 0:
        return 0.0
    raw = 1.0 - math.exp(-0.25 * specs_calibrated)
    return round(min(0.95, raw), 2)
