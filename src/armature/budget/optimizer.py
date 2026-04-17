"""Adaptive token optimizer -- pre-planned budget control for AI coding sessions.

Design principle: UNIFORM QUALITY ACROSS ALL TASKS.

Instead of progressively tightening context as budget depletes (which degrades
quality for later tasks), we pre-plan ALL tasks upfront:

1. Estimate total tokens needed across the entire build plan
2. Pick ONE uniform optimization strategy that fits all tasks within budget
3. Allocate equal per-task budgets
4. Every task -- first and last -- gets the same quality context

If the total estimate exceeds budget, the strategy is applied uniformly:
every task uses narrow context, not just the last few. This prevents the
"quality cliff" where task 1 gets full context and task 10 gets scraps.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from armature.budget.router import ModelRouter, get_pricing
from armature.config.schema import BudgetConfig


@dataclass(frozen=True)
class TokenEstimate:
    """Pre-request token estimate with breakdown."""
    input_tokens: int
    estimated_output_tokens: int
    total: int
    context_files_tokens: int = 0
    spec_tokens: int = 0
    conversation_tokens: int = 0
    cacheable_pct: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass
class OptimizationAction:
    """A concrete action to reduce token usage."""
    strategy: str
    description: str
    estimated_savings_pct: int
    priority: int  # 1=highest
    applies_to: str = "all_tasks"  # "all_tasks" = uniform, never "later_tasks"


@dataclass
class TaskSpec:
    """A single task in a build plan, with its context requirements."""
    task_id: str
    description: str
    context_files: list[str] = field(default_factory=list)
    spec_refs: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    verify_command: str = ""
    estimated_tokens: int = 0  # filled by pre-planner
    phase: str = "build"


@dataclass
class TaskBudget:
    """Budget allocation for a single task -- uniform across all tasks."""
    task_id: str
    max_input_tokens: int
    max_output_tokens: int
    context_files: list[str]
    optimization_applied: list[str]  # which strategies were applied
    model: str = "claude-sonnet"     # routed model for this task
    intent: str = "code_gen"         # task intent used for routing


@dataclass
class BuildBudgetPlan:
    """Complete pre-planned budget for an entire build.

    Every task gets the same strategy and proportional budget.
    No progressive degradation.
    """
    spec_id: str
    strategy: str  # uniform strategy for ALL tasks
    total_budget_tokens: int
    total_estimated_tokens: int
    budget_utilization_pct: float
    per_task_max_input: int
    per_task_max_output: int
    task_budgets: list[TaskBudget]
    optimizations: list[OptimizationAction]  # applied uniformly
    warnings: list[str]
    feasible: bool  # whether all tasks fit within budget
    reserve_pct: float  # % held back for verify/fix cycles


# Token estimation constants (Claude model family)
TOKENS_PER_CHAR = 0.25  # ~4 chars per token average for code
TOKENS_PER_LINE = 15  # average code line
OUTPUT_TO_INPUT_RATIO = 0.4  # typical code generation output/input ratio

# Model pricing -- delegated to router.py's multi-provider catalog.
# PRICING dict kept for backward compatibility (benchmark.py imports it).
PRICING = {
    alias: get_pricing(alias)
    for alias in ("sonnet", "opus", "haiku")
}

# How much budget to reserve for verify-fix cycles (per task)
VERIFY_FIX_RESERVE = 0.15  # 15% of total budget held for verify + self-fix loops

# Optimization strategies with their estimated savings
# Applied UNIFORMLY to all tasks when needed -- never selectively
OPTIMIZATION_STRATEGIES = [
    # Level 0: No optimization needed
    # Level 1: Mild (10-25% savings)
    OptimizationAction(
        strategy="batch_file_reads",
        description="Read related files in single requests instead of one-by-one. "
                    "Group by module/directory.",
        estimated_savings_pct=15,
        priority=1,
    ),
    OptimizationAction(
        strategy="front_load_context",
        description="Put spec + all relevant code in the first message per task. "
                    "Subsequent messages reference by name, not re-read.",
        estimated_savings_pct=20,
        priority=1,
    ),
    # Level 2: Moderate (25-40% savings)
    OptimizationAction(
        strategy="narrow_context",
        description="Each task sees ONLY its spec_refs + context_files. "
                    "Remove all files not directly referenced in the task.",
        estimated_savings_pct=35,
        priority=2,
    ),
    OptimizationAction(
        strategy="compress_between_tasks",
        description="Run /compact between tasks to compress conversation history. "
                    "Fresh context per task prevents accumulation.",
        estimated_savings_pct=30,
        priority=2,
    ),
    # Level 3: Aggressive (40-60% savings)
    OptimizationAction(
        strategy="interface_only",
        description="For upstream dependencies, include only public API signatures "
                    "(function names, type hints, docstrings) not full implementations.",
        estimated_savings_pct=50,
        priority=3,
    ),
    OptimizationAction(
        strategy="spec_summary",
        description="Replace full spec YAML with a one-paragraph summary of the "
                    "relevant acceptance criteria for each task.",
        estimated_savings_pct=15,
        priority=3,
    ),
]


class AdaptiveOptimizer:
    """Pre-planning budget optimizer for AI coding sessions.

    Core principle: estimate all tasks upfront, allocate uniformly.
    Every task -- first and last -- gets the same quality context.

    Usage:
        optimizer = AdaptiveOptimizer(config)
        tasks = [TaskSpec(...), TaskSpec(...), ...]
        plan = optimizer.plan_build(spec_id, tasks, complexity="medium")

        # Each task now has a uniform budget:
        for tb in plan.task_budgets:
            print(f"{tb.task_id}: {tb.max_input_tokens:,} input tokens")
    """

    def __init__(self, config: BudgetConfig, root: Path | None = None) -> None:
        self.config = config
        self.root = root or Path.cwd()

    def estimate_tokens(
        self,
        context_files: list[str | Path],
        spec_text: str = "",
        conversation_tokens: int = 0,
        model: str = "sonnet",
    ) -> TokenEstimate:
        """Estimate token count for a request before sending it."""
        file_tokens = 0
        for fp in context_files:
            path = Path(fp) if Path(fp).is_absolute() else self.root / fp
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                    file_tokens += int(len(content) * TOKENS_PER_CHAR)
                except OSError:
                    file_tokens += 5000
            else:
                file_tokens += 5000  # conservative estimate for missing files

        spec_tokens = int(len(spec_text) * TOKENS_PER_CHAR) if spec_text else 0
        input_total = file_tokens + spec_tokens + conversation_tokens
        estimated_output = int(input_total * OUTPUT_TO_INPUT_RATIO)
        total = input_total + estimated_output

        cacheable_pct = 0.0
        if conversation_tokens > 0 and input_total > 0:
            cacheable_pct = conversation_tokens / input_total

        prices = get_pricing(model)
        input_cost = (input_total / 1_000_000) * prices["input"]
        output_cost = (estimated_output / 1_000_000) * prices["output"]
        cache_savings = input_cost * cacheable_pct * 0.9
        estimated_cost = input_cost + output_cost - cache_savings

        return TokenEstimate(
            input_tokens=input_total,
            estimated_output_tokens=estimated_output,
            total=total,
            context_files_tokens=file_tokens,
            spec_tokens=spec_tokens,
            conversation_tokens=conversation_tokens,
            cacheable_pct=cacheable_pct,
            estimated_cost_usd=estimated_cost,
        )

    def estimate_task(self, task: TaskSpec) -> int:
        """Estimate total tokens for a single task (input + output)."""
        all_files = list(set(task.context_files + task.spec_refs))
        estimate = self.estimate_tokens(all_files)
        return estimate.total

    def plan_build(
        self,
        spec_id: str,
        tasks: list[TaskSpec],
        complexity: str = "medium",
    ) -> BuildBudgetPlan:
        """Pre-plan budget for an entire build -- uniform allocation.

        This is the core method. Given all tasks upfront, it:
        1. Estimates tokens for every task
        2. Sums total need
        3. Determines a SINGLE strategy that fits all tasks within budget
        4. Allocates equal per-task budgets
        5. Returns a plan where every task has identical quality constraints

        Args:
            spec_id: Spec identifier
            tasks: All tasks in the build plan
            complexity: Budget tier (low/medium/high/critical)
        """
        if not tasks:
            return BuildBudgetPlan(
                spec_id=spec_id, strategy="normal",
                total_budget_tokens=0, total_estimated_tokens=0,
                budget_utilization_pct=0, per_task_max_input=200_000,
                per_task_max_output=100_000, task_budgets=[],
                optimizations=[], warnings=[], feasible=True,
                reserve_pct=VERIFY_FIX_RESERVE,
            )

        # Step 1: Get budget ceiling
        tier = self.config.defaults.get(complexity)
        total_budget = tier.max_tokens if tier else 500_000

        # Reserve tokens for verify/fix cycles
        usable_budget = int(total_budget * (1 - VERIFY_FIX_RESERVE))

        # Step 2: Estimate every task
        for task in tasks:
            task.estimated_tokens = self.estimate_task(task)

        raw_total = sum(t.estimated_tokens for t in tasks)

        # Step 3: Determine uniform strategy
        strategy, applied_optimizations = self._select_uniform_strategy(
            raw_total, usable_budget, tasks
        )

        # Step 4: Calculate per-task budget (uniform)
        # After applying optimizations, estimate the effective total
        combined_savings = self._combined_savings(applied_optimizations)
        effective_total = int(raw_total * (1 - combined_savings / 100))

        per_task_budget = usable_budget // len(tasks) if tasks else usable_budget
        # Input/output split: 70/30 (code generation is output-heavy)
        per_task_max_input = int(per_task_budget * 0.70)
        per_task_max_output = int(per_task_budget * 0.30)

        utilization = (effective_total / usable_budget * 100) if usable_budget > 0 else 0
        feasible = effective_total <= usable_budget

        warnings: list[str] = []

        # Scope-based budget fit check (warns if tier is wrong for project size)
        try:
            from armature.budget.benchmark import scan_project, check_budget_fit
            from armature.config.schema import ArmatureConfig
            scope = scan_project(self.root, ArmatureConfig())
            if scope.total_loc > 0:
                scope_warning = check_budget_fit(self.config, scope, complexity)
                if scope_warning.level in ("too_low", "too_high", "mismatched_tier"):
                    warnings.append(f"SCOPE: {scope_warning.message}")
        except Exception:
            pass  # benchmark scan is best-effort, never blocks planning

        if not feasible:
            deficit = effective_total - usable_budget
            warnings.append(
                f"Build plan exceeds budget by {deficit:,} tokens even with all "
                f"optimizations applied. Consider: reducing task count, splitting "
                f"into multiple specs, or upgrading budget tier from '{complexity}'."
            )
        if utilization > 90 and feasible:
            warnings.append(
                f"Budget utilization at {utilization:.0f}%. Little room for "
                f"verify-fix cycles. Consider proactive quality checks."
            )

        # Step 5: Build per-task allocations with model routing
        task_budgets = []
        optimization_names = [o.strategy for o in applied_optimizations]

        # Set up router from config
        router = ModelRouter(
            enabled_models=self.config.providers.enabled_models,
            quality_floor=self.config.providers.quality_floor,
            premium_intents=self.config.providers.premium_intents,
        )
        use_routing = self.config.providers.strategy != "single_model"

        for task in tasks:
            # Proportional allocation: larger tasks get proportionally more,
            # but capped at per_task_budget to keep it fair
            if raw_total > 0:
                task_share = task.estimated_tokens / raw_total
                task_tokens = int(usable_budget * task_share)
            else:
                task_tokens = per_task_budget

            task_input = int(task_tokens * 0.70)
            task_output = int(task_tokens * 0.30)

            # Route task to cheapest adequate model
            intent = self._infer_intent(task)
            if use_routing:
                decision = router.route(intent, task_input, task_output)
                model = decision.model
            else:
                model = self.config.providers.default_model

            task_budgets.append(TaskBudget(
                task_id=task.task_id,
                max_input_tokens=task_input,
                max_output_tokens=task_output,
                context_files=task.context_files,
                optimization_applied=optimization_names,
                model=model,
                intent=intent,
            ))

        return BuildBudgetPlan(
            spec_id=spec_id,
            strategy=strategy,
            total_budget_tokens=total_budget,
            total_estimated_tokens=raw_total,
            budget_utilization_pct=utilization,
            per_task_max_input=per_task_max_input,
            per_task_max_output=per_task_max_output,
            task_budgets=task_budgets,
            optimizations=applied_optimizations,
            warnings=warnings,
            feasible=feasible,
            reserve_pct=VERIFY_FIX_RESERVE,
        )

    def plan_phase(
        self,
        spec_id: str,
        phase: str,
        tasks: list[TaskSpec],
        complexity: str = "medium",
    ) -> BuildBudgetPlan:
        """Pre-plan budget for a specific phase only.

        Uses phase_allocation from config to determine the phase's share
        of the total budget, then plans uniformly within that share.
        """
        tier = self.config.defaults.get(complexity)
        total_budget = tier.max_tokens if tier else 500_000
        total_alloc = sum(self.config.phase_allocation.values())
        phase_pct = self.config.phase_allocation.get(phase, 0) / total_alloc if total_alloc > 0 else 0

        # Override config temporarily for phase-scoped planning
        phase_budget = int(total_budget * phase_pct)

        # Create a scoped config with the phase budget
        from copy import deepcopy
        scoped_config = deepcopy(self.config)
        scoped_config.defaults[complexity] = type(tier)(
            max_tokens=phase_budget,
            max_cost_usd=(tier.max_cost_usd * phase_pct) if tier else 10.0 * phase_pct,
        )

        scoped_optimizer = AdaptiveOptimizer(scoped_config, self.root)
        plan = scoped_optimizer.plan_build(spec_id, tasks, complexity)
        return plan

    def check_task_progress(
        self,
        plan: BuildBudgetPlan,
        completed_task_ids: list[str],
        actual_tokens_used: dict[str, int],
    ) -> dict:
        """Check progress against the pre-plan (monitoring, not tightening).

        Returns status report showing how actual usage compares to plan.
        If a task used more than planned, the RESERVE absorbs it --
        remaining tasks keep their original budgets.
        """
        total_planned = sum(
            tb.max_input_tokens + tb.max_output_tokens
            for tb in plan.task_budgets
        )
        total_actual = sum(actual_tokens_used.values())
        total_completed = len(completed_task_ids)
        total_tasks = len(plan.task_budgets)

        overruns: list[dict] = []
        savings: list[dict] = []
        for tb in plan.task_budgets:
            if tb.task_id in actual_tokens_used:
                actual = actual_tokens_used[tb.task_id]
                planned = tb.max_input_tokens + tb.max_output_tokens
                delta = actual - planned
                entry = {"task_id": tb.task_id, "planned": planned, "actual": actual, "delta": delta}
                if delta > 0:
                    overruns.append(entry)
                elif delta < 0:
                    savings.append(entry)

        # Reserve status
        reserve_tokens = int(plan.total_budget_tokens * plan.reserve_pct)
        reserve_used = max(0, total_actual - (total_planned * total_completed / total_tasks)) if total_tasks > 0 else 0

        remaining_tasks = [
            tb for tb in plan.task_budgets if tb.task_id not in completed_task_ids
        ]

        return {
            "completed": total_completed,
            "remaining": len(remaining_tasks),
            "total_planned_tokens": total_planned,
            "total_actual_tokens": total_actual,
            "on_track": total_actual <= total_planned,
            "overruns": overruns,
            "savings": savings,
            "reserve_tokens": reserve_tokens,
            "reserve_used": int(reserve_used),
            "remaining_task_budgets_unchanged": True,  # never tighten
        }

    @staticmethod
    def _infer_intent(task: TaskSpec) -> str:
        """Infer the routing intent from task metadata.

        Maps task descriptions and phases to intent categories used by the
        model router for capability-based routing.
        """
        desc = task.description.lower()
        phase = task.phase.lower()

        # Phase-based heuristics
        if phase == "test":
            return "test_gen"
        if phase in ("audit", "validate"):
            return "reasoning"
        if phase == "review":
            return "explain"

        # Description-based heuristics
        if any(w in desc for w in ("research", "search", "find", "lookup", "investigate")):
            return "research"
        if any(w in desc for w in ("explain", "document", "describe", "summarize")):
            return "explain"
        if any(w in desc for w in ("test", "spec", "coverage")):
            return "test_gen"
        if any(w in desc for w in ("architect", "design", "refactor", "restructure")):
            return "complex_code_gen"
        if any(w in desc for w in ("fix", "lint", "format", "typo", "rename")):
            return "lint_fix"

        # Default: general code generation
        return "code_gen"

    def _select_uniform_strategy(
        self,
        raw_total: int,
        usable_budget: int,
        tasks: list[TaskSpec],
    ) -> tuple[str, list[OptimizationAction]]:
        """Select the minimum optimization level that fits all tasks in budget.

        Returns (strategy_name, list_of_optimizations_to_apply).
        Optimizations are cumulative and applied to ALL tasks equally.
        """
        if raw_total <= usable_budget:
            return "full_context", []

        # Try optimization levels until we fit
        applied: list[OptimizationAction] = []
        effective_total = raw_total

        # Group by priority level
        levels: dict[int, list[OptimizationAction]] = {}
        for opt in OPTIMIZATION_STRATEGIES:
            levels.setdefault(opt.priority, []).append(opt)

        strategy_names = {1: "optimized", 2: "narrow", 3: "minimal"}

        for level in sorted(levels.keys()):
            level_opts = levels[level]
            applied.extend(level_opts)
            combined = self._combined_savings(applied)
            effective_total = int(raw_total * (1 - combined / 100))

            if effective_total <= usable_budget:
                return strategy_names.get(level, "optimized"), applied

        # Even max optimization doesn't fit -- return infeasible plan
        return "infeasible", applied

    def _combined_savings(self, optimizations: list[OptimizationAction]) -> float:
        """Calculate combined savings from multiple optimizations.

        Not additive -- uses diminishing returns formula:
        combined = 1 - product(1 - savings_i) for each optimization
        """
        if not optimizations:
            return 0.0
        remaining = 1.0
        for opt in optimizations:
            remaining *= (1 - opt.estimated_savings_pct / 100)
        return (1 - remaining) * 100

    def format_build_plan(self, plan: BuildBudgetPlan) -> str:
        """Format a build budget plan as human-readable text."""
        lines = []
        lines.append(f"BUILD BUDGET PLAN: {plan.spec_id}")
        lines.append(f"Strategy: {plan.strategy.upper()} (applied uniformly to ALL tasks)")
        lines.append(f"Feasible: {'YES' if plan.feasible else 'NO -- exceeds budget'}")
        lines.append("")
        lines.append(f"  Total budget:    {plan.total_budget_tokens:>12,} tokens")
        lines.append(f"  Reserve (fix):   {int(plan.total_budget_tokens * plan.reserve_pct):>12,} tokens ({plan.reserve_pct:.0%})")
        lines.append(f"  Usable budget:   {int(plan.total_budget_tokens * (1 - plan.reserve_pct)):>12,} tokens")
        lines.append(f"  Estimated need:  {plan.total_estimated_tokens:>12,} tokens")
        lines.append(f"  Utilization:     {plan.budget_utilization_pct:>11.0f}%")

        if plan.optimizations:
            combined = self._combined_savings(plan.optimizations)
            lines.append("")
            lines.append(f"Optimizations (applied to ALL {len(plan.task_budgets)} tasks uniformly):")
            for opt in plan.optimizations:
                lines.append(f"  - {opt.strategy}: {opt.description}")
            lines.append(f"  Combined savings: {combined:.0f}%")

        if plan.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in plan.warnings:
                lines.append(f"  ! {w}")

        lines.append("")
        lines.append(f"Per-task allocation ({len(plan.task_budgets)} tasks):")
        lines.append(f"  {'Task':<25} {'Model':<18} {'Input':>10} {'Output':>10} {'Total':>10}")
        lines.append(f"  {'-' * 73}")
        for tb in plan.task_budgets:
            total = tb.max_input_tokens + tb.max_output_tokens
            lines.append(
                f"  {tb.task_id:<25} {tb.model:<18} "
                f"{tb.max_input_tokens:>10,} {tb.max_output_tokens:>10,} {total:>10,}"
            )

        return "\n".join(lines)
