"""Project scope analysis and budget benchmarking.

Scans a project to measure scope (LOC, files, layers, specs), calculates
benchmark costs per task type, and warns when configured budget is too low
(quality will suffer) or too high (wasteful).

Design: benchmark BEFORE work starts, not during. The warning fires at
armature init, armature budget --benchmark, and armature budget --pre-plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from armature.budget.optimizer import OUTPUT_TO_INPUT_RATIO
from armature.budget.router import get_pricing
from armature.config.schema import ArmatureConfig, BudgetConfig

# --- Dataclasses ---

@dataclass
class ProjectScope:
    """Measured project scope metrics."""
    language: str
    framework: str
    total_source_files: int
    total_loc: int
    total_test_files: int
    test_loc: int
    architectural_layers: int
    boundary_rules: int
    conformance_rules: int
    spec_count: int
    ac_count: int


@dataclass
class TaskEstimate:
    """Estimated budget for a specific task type."""
    task_type: str
    estimated_tokens: int
    estimated_cost_usd: float
    model: str


@dataclass
class BudgetBenchmark:
    """Benchmark cost calculation for a project scope."""
    scope: ProjectScope
    estimates: dict[str, TaskEstimate]
    recommended_tier: str
    recommended_tokens: int
    recommended_cost_usd: float


@dataclass
class ScopeWarning:
    """Warning about budget-scope mismatch."""
    level: str  # "too_low" | "too_high" | "right_sized" | "mismatched_tier"
    message: str
    configured_tokens: int
    benchmark_tokens: int
    recommended_tier: str


# --- Constants ---

# Source file extensions per language
SOURCE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "typescript": [".ts", ".tsx", ".js", ".jsx"],
    "go": [".go"],
    "rust": [".rs"],
}

# Test file patterns per language
TEST_PATTERNS: dict[str, list[str]] = {
    "python": ["test_*.py", "*_test.py", "conftest.py"],
    "typescript": ["*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx"],
    "go": ["*_test.go"],
    "rust": [],  # Rust tests are inline
}

# Task type read multipliers: how much of the codebase a task typically touches
TASK_MULTIPLIERS: dict[str, float] = {
    "bugfix": 1.5,
    "feature": 3.0,
    "refactor": 2.0,
    "spike": 0.5,
    "test": 2.5,
}

# Language verbosity/complexity multiplier
LANGUAGE_MULTIPLIERS: dict[str, float] = {
    "python": 1.0,
    "typescript": 1.1,
    "go": 0.8,
    "rust": 0.9,
}

# Framework complexity multiplier (larger frameworks need more context)
FRAMEWORK_MULTIPLIERS: dict[str, float] = {
    "django": 1.3,
    "fastapi": 1.0,
    "flask": 0.9,
    "nextjs": 1.2,
    "express": 0.9,
    "react": 1.1,
    "vue": 1.0,
}

# Architecture layer complexity multiplier
def _arch_multiplier(layer_count: int) -> float:
    if layer_count <= 2:
        return 1.0
    elif layer_count <= 4:
        return 1.2
    elif layer_count <= 7:
        return 1.4
    else:
        return 1.6


# Budget tier thresholds for recommendation
TIER_THRESHOLDS = [
    ("low", 100_000, 2.0),
    ("medium", 500_000, 10.0),
    ("high", 1_000_000, 20.0),
    ("critical", 2_000_000, 40.0),
]


# --- Scanner ---

def scan_project(root: Path, config: ArmatureConfig) -> ProjectScope:
    """Scan project directory to measure scope metrics.

    Counts source files, LOC, test files, and reads architectural
    complexity from armature.yaml config.
    """
    language = config.project.language
    src_dir = root / config.project.src_dir
    test_dir = root / config.project.test_dir

    extensions = SOURCE_EXTENSIONS.get(language, [".py"])

    # Count source files and LOC
    source_files = 0
    source_loc = 0
    if src_dir.exists():
        for ext in extensions:
            for f in src_dir.rglob(f"*{ext}"):
                if _is_test_file(f, language):
                    continue
                source_files += 1
                source_loc += _count_loc(f)

    # Count test files and LOC
    test_files = 0
    test_loc = 0
    if test_dir.exists():
        for ext in extensions:
            for f in test_dir.rglob(f"*{ext}"):
                test_files += 1
                test_loc += _count_loc(f)

    # Architecture complexity from config
    arch_layers = len(config.architecture.layers)
    boundary_rules = len(config.architecture.boundaries)
    conformance_rules = len(config.architecture.conformance)

    # Spec count and AC count
    spec_count = 0
    ac_count = 0
    if config.specs.enabled:
        spec_dir = root / config.specs.dir
        if spec_dir.exists():
            for spec_file in spec_dir.glob("*.yaml"):
                spec_count += 1
                ac_count += _count_acceptance_criteria(spec_file)
            for spec_file in spec_dir.glob("*.yml"):
                spec_count += 1
                ac_count += _count_acceptance_criteria(spec_file)

    return ProjectScope(
        language=language,
        framework=config.project.framework,
        total_source_files=source_files,
        total_loc=source_loc,
        total_test_files=test_files,
        test_loc=test_loc,
        architectural_layers=arch_layers,
        boundary_rules=boundary_rules,
        conformance_rules=conformance_rules,
        spec_count=spec_count,
        ac_count=ac_count,
    )


# --- Benchmark Calculator ---

def calculate_benchmark(
    scope: ProjectScope,
    model: str = "sonnet",
    calibration: dict | None = None,
) -> BudgetBenchmark:
    """Calculate cost benchmarks from project scope metrics.

    Uses empirical formulas:
      base_tokens = LOC * TOKENS_PER_LOC
      task_tokens = base_tokens * task_multiplier * lang_multiplier
                    * framework_multiplier * arch_multiplier
                    * calibration_adjustment
      task_cost = (input_tokens/1M * input_price) + (output_tokens/1M * output_price)
                  * (1 - cache_hit_rate * 0.9)

    Args:
        scope: Project scope metrics from scan_project()
        model: Model for cost estimation
        calibration: Optional calibration overrides from apply_calibration().
                     Keys: task_adjustments, model_verbosity, cache_hit_rate
    """
    cal = calibration or {}
    task_adj = cal.get("task_adjustments", {})
    model_verb = cal.get("model_verbosity", {})
    cache_rate = cal.get("cache_hit_rate", 0.0)

    # Base: tokens to represent the codebase
    # Each line of code ~ 15 tokens (TOKENS_PER_LINE), but we also need
    # output tokens. Use TOKENS_PER_CHAR for precision.
    # Average line length ~ 60 chars → ~15 tokens per line
    base_tokens = int(scope.total_loc * 15)  # tokens to read entire codebase

    lang_mult = LANGUAGE_MULTIPLIERS.get(scope.language, 1.0)
    fw_mult = FRAMEWORK_MULTIPLIERS.get(scope.framework, 1.0)
    arch_mult = _arch_multiplier(scope.architectural_layers)

    # Model-specific output verbosity adjustment
    verbosity = model_verb.get(model, 1.0)
    effective_output_ratio = OUTPUT_TO_INPUT_RATIO * verbosity

    prices = get_pricing(model)

    # Cache savings factor
    cache_factor = 1.0 - (cache_rate * 0.9)

    estimates: dict[str, TaskEstimate] = {}
    for task_type, task_mult in TASK_MULTIPLIERS.items():
        # Apply calibration adjustment for this task type
        cal_adj = task_adj.get(task_type, 1.0)

        # Input: reading context files proportional to task scope
        input_tokens = int(base_tokens * task_mult * lang_mult * fw_mult * arch_mult * cal_adj)
        # Output: code generation adjusted for model verbosity
        output_tokens = int(input_tokens * effective_output_ratio)
        total_tokens = input_tokens + output_tokens

        # Cost: input + output pricing, adjusted for cache hits
        cost = (
            (input_tokens / 1_000_000) * prices["input"] +
            (output_tokens / 1_000_000) * prices["output"]
        ) * cache_factor

        estimates[task_type] = TaskEstimate(
            task_type=task_type,
            estimated_tokens=total_tokens,
            estimated_cost_usd=round(cost, 2),
            model=model,
        )

    # Recommended tier: based on largest task type (feature)
    feature_tokens = estimates["feature"].estimated_tokens
    # Add 2x safety margin for verify/fix cycles and conversation overhead
    recommended_tokens = feature_tokens * 2

    recommended_tier = "low"
    recommended_cost = 2.0
    for tier_name, tier_tokens, tier_cost in TIER_THRESHOLDS:
        if recommended_tokens <= tier_tokens:
            recommended_tier = tier_name
            recommended_cost = tier_cost
            break
    else:
        recommended_tier = "critical"
        recommended_cost = 40.0

    return BudgetBenchmark(
        scope=scope,
        estimates=estimates,
        recommended_tier=recommended_tier,
        recommended_tokens=recommended_tokens,
        recommended_cost_usd=recommended_cost,
    )


# --- Budget Fit Check ---

def check_budget_fit(
    config: BudgetConfig,
    scope: ProjectScope,
    complexity: str = "medium",
    model: str = "sonnet",
) -> ScopeWarning:
    """Check if configured budget matches project scope.

    Returns a ScopeWarning indicating whether the budget is:
    - too_low: will degrade quality (budget < 60% of benchmark)
    - right_sized: good fit (60%-500% of benchmark)
    - too_high: wasteful (budget > 500% of benchmark)
    - mismatched_tier: wrong tier selected for this scope
    """
    benchmark = calculate_benchmark(scope, model)
    feature_est = benchmark.estimates["feature"]

    tier = config.defaults.get(complexity)
    if tier is None:
        return ScopeWarning(
            level="right_sized",
            message=f"No budget tier '{complexity}' configured.",
            configured_tokens=0,
            benchmark_tokens=feature_est.estimated_tokens,
            recommended_tier=benchmark.recommended_tier,
        )

    configured = tier.max_tokens
    benchmark_tokens = feature_est.estimated_tokens
    ratio = configured / benchmark_tokens if benchmark_tokens > 0 else 1.0

    if ratio < 0.6:
        return ScopeWarning(
            level="too_low",
            message=(
                f"Budget is undersized for this project scope. "
                f"Configured: {configured:,} tokens ({complexity} tier). "
                f"Benchmark for a feature task: {benchmark_tokens:,} tokens. "
                f"At {ratio:.1f}x benchmark, quality will be degraded for every task. "
                f"Recommended: '{benchmark.recommended_tier}' tier "
                f"({benchmark.recommended_tokens:,} tokens)."
            ),
            configured_tokens=configured,
            benchmark_tokens=benchmark_tokens,
            recommended_tier=benchmark.recommended_tier,
        )
    elif ratio > 5.0:
        return ScopeWarning(
            level="too_high",
            message=(
                f"Budget is significantly oversized for this project scope. "
                f"Configured: {configured:,} tokens ({complexity} tier). "
                f"Benchmark for a feature task: {benchmark_tokens:,} tokens. "
                f"At {ratio:.1f}x benchmark, budget is wasteful. "
                f"A '{benchmark.recommended_tier}' tier "
                f"({benchmark.recommended_tokens:,} tokens) covers the largest "
                f"feature with 2x safety margin."
            ),
            configured_tokens=configured,
            benchmark_tokens=benchmark_tokens,
            recommended_tier=benchmark.recommended_tier,
        )
    elif complexity != benchmark.recommended_tier:
        return ScopeWarning(
            level="mismatched_tier",
            message=(
                f"Budget tier '{complexity}' ({configured:,} tokens) works but "
                f"scope analysis suggests '{benchmark.recommended_tier}' tier "
                f"({benchmark.recommended_tokens:,} tokens) is a better fit. "
                f"Benchmark for a feature task: {benchmark_tokens:,} tokens."
            ),
            configured_tokens=configured,
            benchmark_tokens=benchmark_tokens,
            recommended_tier=benchmark.recommended_tier,
        )
    else:
        return ScopeWarning(
            level="right_sized",
            message=(
                f"Budget is well-sized for this project scope. "
                f"Configured: {configured:,} tokens ({complexity} tier). "
                f"Benchmark: {benchmark_tokens:,} tokens. Ratio: {ratio:.1f}x."
            ),
            configured_tokens=configured,
            benchmark_tokens=benchmark_tokens,
            recommended_tier=benchmark.recommended_tier,
        )


# --- Helpers ---

def _count_loc(file_path: Path) -> int:
    """Count non-blank, non-comment lines in a file."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0

    count = 0
    in_docstring = False
    for line in content.split("\n"):
        stripped = line.strip()
        # Python docstrings
        if '"""' in stripped or "'''" in stripped:
            if in_docstring:
                in_docstring = False
                continue
            elif stripped.count('"""') == 1 or stripped.count("'''") == 1:
                in_docstring = True
                continue
        if in_docstring:
            continue
        # Skip blank lines and single-line comments
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        count += 1
    return count


def _is_test_file(file_path: Path, language: str) -> bool:
    """Check if a file is a test file."""
    name = file_path.name.lower()
    if language == "python":
        return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"
    elif language == "typescript":
        return ".test." in name or ".spec." in name
    elif language == "go":
        return name.endswith("_test.go")
    return False


def _count_acceptance_criteria(spec_path: Path) -> int:
    """Count acceptance criteria in a spec YAML file."""
    try:
        content = spec_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    # Match lines like "  - AC-1:" or "  - id: AC-1"
    return len(re.findall(r"AC-\d+", content))


def format_benchmark(
    benchmark: BudgetBenchmark,
    industry_comparison: object | None = None,
) -> str:
    """Format benchmark results as human-readable text.

    Args:
        benchmark: Benchmark results from calculate_benchmark()
        industry_comparison: Optional IndustryComparison from calibrator.compare_against_industry()
    """
    scope = benchmark.scope
    lines = []

    lines.append("PROJECT SCOPE ANALYSIS")
    lines.append("=" * 40)
    lines.append(f"  Language:           {scope.language}")
    if scope.framework:
        lines.append(f"  Framework:          {scope.framework}")
    lines.append(f"  Source files:       {scope.total_source_files}")
    lines.append(f"  Lines of code:      {scope.total_loc:,}")
    lines.append(f"  Test files:         {scope.total_test_files}")
    lines.append(f"  Test LOC:           {scope.test_loc:,}")
    if scope.architectural_layers > 0:
        lines.append(f"  Architecture:       {scope.architectural_layers} layers, "
                      f"{scope.boundary_rules} boundary rules")
    if scope.conformance_rules > 0:
        lines.append(f"  Conformance rules:  {scope.conformance_rules}")
    if scope.spec_count > 0:
        lines.append(f"  Specs:              {scope.spec_count} specs, "
                      f"{scope.ac_count} acceptance criteria")

    model = next(iter(benchmark.estimates.values())).model if benchmark.estimates else "sonnet"
    lines.append(f"\nCOST BENCHMARKS ({model.capitalize()})")
    lines.append("=" * 40)
    lines.append(f"  {'Task Type':<15} {'Est. Tokens':>12} {'Est. Cost':>12}")
    lines.append(f"  {'-' * 39}")

    for task_type in ["bugfix", "feature", "refactor", "spike", "test"]:
        if task_type in benchmark.estimates:
            est = benchmark.estimates[task_type]
            lines.append(f"  {est.task_type:<15} {est.estimated_tokens:>12,} "
                          f"${est.estimated_cost_usd:>10.2f}")

    lines.append(f"\n  Recommended tier:   {benchmark.recommended_tier} "
                  f"({benchmark.recommended_tokens:,} tokens / "
                  f"${benchmark.recommended_cost_usd:.2f})")

    # Append industry comparison if provided
    if industry_comparison is not None:
        from armature.budget.calibrator import format_industry_comparison
        lines.append("")
        lines.append(format_industry_comparison(industry_comparison))

    return "\n".join(lines)


def format_warning(warning: ScopeWarning) -> str:
    """Format a scope warning as human-readable text."""
    lines = []
    lines.append("BUDGET FIT CHECK")
    lines.append("=" * 40)
    lines.append(f"  Configured:   {warning.configured_tokens:,} tokens")
    lines.append(f"  Benchmark:    {warning.benchmark_tokens:,} tokens (feature task)")

    if warning.benchmark_tokens > 0:
        ratio = warning.configured_tokens / warning.benchmark_tokens
        lines.append(f"  Ratio:        {ratio:.1f}x benchmark")

    if warning.level == "too_low" or warning.level == "too_high":
        lines.append(f"\n  [!] WARNING: {warning.message}")
    elif warning.level == "mismatched_tier":
        lines.append(f"\n  [~] NOTE: {warning.message}")
    else:
        lines.append(f"\n  [OK] {warning.message}")

    return "\n".join(lines)
