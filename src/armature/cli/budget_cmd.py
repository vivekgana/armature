"""armature budget -- cost tracking, reporting, and pre-planned optimization."""

from __future__ import annotations

import json

import click

from armature._internal.output import console, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--report", "report_spec", help="Generate cost report for a spec ID")
@click.option("--spec", "spec_id", help="Spec ID for logging or optimization")
@click.option("--phase", help="Development phase (validate, audit, plan, build, test, review)")
@click.option("--tokens", type=int, help="Token count to log")
@click.option("--cost", "cost_usd", type=float, help="Cost in USD to log")
@click.option("--pre-plan", "preplan_file", help="Pre-plan budget for a build plan JSON file")
@click.option("--plan", "plan_files", help="Comma-separated files to plan request batching for")
@click.option("--estimate", "estimate_files", help="Comma-separated files to estimate tokens for")
@click.option("--progress", "progress_file", help="Check progress against a pre-plan JSON file")
@click.option("--benchmark", "do_benchmark", is_flag=True,
              help="Scan project scope and check if budget tiers are right-sized")
@click.option("--by-provider", "by_provider", is_flag=True,
              help="Show per-provider cost breakdown (requires --report)")
@click.option("--trends", "show_trends", is_flag=True,
              help="Show cross-spec cost trends")
@click.option("--calibrate", "calibrate_spec", help="Calibrate multipliers from a completed spec")
@click.option("--calibration-status", "show_calibration", is_flag=True,
              help="Show current calibration profile")
@click.option("--cache-stats", "show_cache_stats", is_flag=True,
              help="Show semantic cache statistics")
@click.option("--industry", "show_industry", is_flag=True,
              help="Show industry benchmark comparison (with --benchmark or --report)")
@click.option("--complexity", default="medium", help="Budget complexity tier (low/medium/high/critical)")
@click.option("--model", default="sonnet", help="Model for cost estimation (any supported model)")
@click.option("--json-out", "json_output", is_flag=True, help="Output as JSON")
def budget_cmd(
    report_spec: str | None,
    spec_id: str | None,
    phase: str | None,
    tokens: int | None,
    cost_usd: float | None,
    preplan_file: str | None,
    plan_files: str | None,
    estimate_files: str | None,
    progress_file: str | None,
    do_benchmark: bool,
    by_provider: bool,
    show_trends: bool,
    calibrate_spec: str | None,
    show_calibration: bool,
    show_cache_stats: bool,
    show_industry: bool,
    complexity: str,
    model: str,
    json_output: bool,
) -> None:
    """Track session costs and generate budget reports.

    Pre-planned optimization: estimate ALL tasks upfront, allocate uniform
    per-task budgets. Every task gets equal quality context -- no degradation.
    """
    config = load_config_or_defaults()

    if do_benchmark:
        _handle_benchmark(config, complexity, model, json_output, show_industry)
        return

    if not config.budget.enabled:
        console.print("[yellow]Budget tracking is disabled in armature.yaml[/yellow]")
        return

    from armature.budget.reporter import generate_provider_report, generate_report, generate_trend_report
    from armature.budget.tracker import SessionTracker

    tracker = SessionTracker(config.budget)

    if show_trends:
        print_header("Cost Trends")
        generate_trend_report(tracker)
        return

    if show_calibration:
        _handle_calibration_status(config)
        return

    if calibrate_spec:
        _handle_calibrate(config, calibrate_spec)
        return

    if show_cache_stats and spec_id:
        _handle_cache_stats(tracker, spec_id)
        return

    if report_spec and by_provider:
        print_header(f"Provider Report: {report_spec}")
        generate_provider_report(tracker, report_spec, config.budget)
        return

    if report_spec:
        print_header(f"Budget Report: {report_spec}")
        generate_report(tracker, report_spec, config.budget)
        if show_industry:
            _handle_industry_report(config, tracker, report_spec, model)

    elif preplan_file:
        _handle_preplan(config, preplan_file, complexity, json_output)

    elif estimate_files:
        _handle_estimate(config, estimate_files, json_output)

    elif plan_files:
        _handle_plan(plan_files, json_output)

    elif progress_file and spec_id:
        _handle_progress(config, tracker, spec_id, progress_file, complexity)

    elif spec_id and phase and tokens is not None:
        tracker.log(spec_id, phase, tokens, cost_usd or 0.0)
        console.print(f"[green]Logged:[/green] {spec_id}/{phase} -- {tokens:,} tokens, ${cost_usd or 0:.2f}")

    else:
        console.print("Usage:")
        console.print("  armature budget --benchmark                          # Scope analysis + budget fit check")
        console.print("  armature budget --benchmark --model opus             # Benchmark with Opus pricing")
        console.print("  armature budget --benchmark --industry               # Benchmark with industry comparison")
        console.print("  armature budget --report SPEC-ID                     # Cost report for a spec")
        console.print("  armature budget --report SPEC-ID --by-provider       # Per-provider breakdown")
        console.print("  armature budget --report SPEC-ID --industry          # Industry benchmark comparison")
        console.print("  armature budget --trends                             # Cross-spec cost trends")
        console.print("  armature budget --spec SPEC-ID --phase build --tokens 50000 --cost 1.25")
        console.print("  armature budget --pre-plan build-plan.json --complexity medium")
        console.print("  armature budget --estimate file1.py,file2.py")
        console.print("  armature budget --plan file1.py,file2.py,file3.py")
        console.print("  armature budget --progress build-plan.json --spec SPEC-ID")
        console.print("  armature budget --calibrate SPEC-ID                  # Calibrate from completed spec")
        console.print("  armature budget --calibration-status                 # Show calibration profile")
        console.print("  armature budget --cache-stats --spec SPEC-ID         # Semantic cache stats")


def _handle_benchmark(
    config, complexity: str, model: str, json_output: bool, show_industry: bool = False,
) -> None:
    """Scan project scope and check if budget tiers are right-sized."""
    from pathlib import Path

    from armature.budget.benchmark import (
        calculate_benchmark,
        check_budget_fit,
        format_benchmark,
        format_warning,
        scan_project,
    )

    root = Path.cwd()
    scope = scan_project(root, config)
    benchmark = calculate_benchmark(scope, model)

    # Build industry comparison if requested
    industry_comparison = None
    if show_industry:
        from armature.budget.calibrator import compare_against_industry
        from armature.budget.tracker import SessionTracker

        if config.budget.enabled:
            tracker = SessionTracker(config.budget)
            # Use most recent spec if available, or empty comparison
            specs = tracker.list_specs()
            spec_id = specs[-1] if specs else ""
            industry_comparison = compare_against_industry(benchmark, tracker, spec_id)
        else:
            # No tracker available -- use benchmark-only comparison with a stub tracker
            from armature.budget.calibrator import (
                INDUSTRY_PHASE_TARGETS,
                INDUSTRY_TASK_TARGETS,
                IndustryComparison,
                assess_quality_budget_position,
            )
            quality_pct, quality_note = assess_quality_budget_position(benchmark.recommended_tokens)
            # Build a benchmark-only comparison (no actuals)
            task_positions = {}
            for task_type, targets in INDUSTRY_TASK_TARGETS.items():
                est = benchmark.estimates.get(task_type)
                actual = est.estimated_tokens if est else 0
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
                    "actual": actual, "p25": p25, "median": median, "p75": p75,
                    "percentile_label": label,
                }

            total_industry = sum(
                t.read_tokens_per_loc + t.write_tokens_per_loc
                for t in INDUSTRY_PHASE_TARGETS.values()
            )
            phase_comparison = {}
            for phase, target in INDUSTRY_PHASE_TARGETS.items():
                industry_pct = ((target.read_tokens_per_loc + target.write_tokens_per_loc)
                                / total_industry * 100) if total_industry > 0 else 0
                phase_comparison[phase] = {
                    "actual_pct": 0.0, "industry_pct": round(industry_pct, 1),
                    "deviation": round(-industry_pct, 1), "source": target.source,
                }

            industry_comparison = IndustryComparison(
                task_positions=task_positions,
                budget_tokens=benchmark.recommended_tokens,
                estimated_quality_pct=quality_pct,
                quality_ceiling_note=quality_note,
                cost_per_loc=None,
                cache_hit_rate=0.0,
                routing_savings_ratio=None,
                calibration_drift=None,
                phase_comparison=phase_comparison,
                grades={},
            )
            from armature.budget.calibrator import compute_efficiency_grades
            industry_comparison.grades = compute_efficiency_grades(industry_comparison)

    if json_output:
        output: dict = {
            "scope": {
                "language": scope.language,
                "framework": scope.framework,
                "source_files": scope.total_source_files,
                "loc": scope.total_loc,
                "test_files": scope.total_test_files,
                "test_loc": scope.test_loc,
                "architectural_layers": scope.architectural_layers,
                "boundary_rules": scope.boundary_rules,
            },
            "benchmarks": {
                task_type: {
                    "tokens": est.estimated_tokens,
                    "cost_usd": est.estimated_cost_usd,
                }
                for task_type, est in benchmark.estimates.items()
            },
            "recommended_tier": benchmark.recommended_tier,
            "recommended_tokens": benchmark.recommended_tokens,
        }

        if config.budget.enabled:
            warning = check_budget_fit(config.budget, scope, complexity, model)
            output["budget_fit"] = {
                "level": warning.level,
                "message": warning.message,
                "configured_tokens": warning.configured_tokens,
                "benchmark_tokens": warning.benchmark_tokens,
                "recommended_tier": warning.recommended_tier,
            }

        if industry_comparison is not None:
            output["industry_comparison"] = {
                "task_positions": industry_comparison.task_positions,
                "budget_tokens": industry_comparison.budget_tokens,
                "estimated_quality_pct": industry_comparison.estimated_quality_pct,
                "quality_ceiling_note": industry_comparison.quality_ceiling_note,
                "grades": industry_comparison.grades,
            }

        console.print(json.dumps(output, indent=2))
    else:
        console.print(format_benchmark(benchmark, industry_comparison))

        if config.budget.enabled:
            warning = check_budget_fit(config.budget, scope, complexity, model)
            console.print("")
            console.print(format_warning(warning))
        else:
            console.print("\n  Budget tracking is disabled. To enable, add to armature.yaml:")
            console.print("    budget:")
            console.print("      enabled: true")
            console.print(f"      # Recommended tier: {benchmark.recommended_tier}")


def _handle_preplan(config, preplan_file: str, complexity: str, json_output: bool) -> None:
    """Pre-plan budget for an entire build -- uniform allocation across all tasks.

    Reads a build plan JSON with task definitions, estimates everything upfront,
    and outputs per-task budgets with a single uniform strategy.

    Build plan JSON format:
    {
        "spec_id": "SPEC-2026-Q2-001",
        "tasks": [
            {
                "task_id": "task-1",
                "description": "Implement user model",
                "context_files": ["src/models/user.py", "src/models/base.py"],
                "spec_refs": ["specs/SPEC-2026-Q2-001.yaml"],
                "output_files": ["src/models/user.py"],
                "verify_command": "pytest tests/test_models/ -x"
            },
            ...
        ]
    }
    """
    from pathlib import Path

    from armature.budget.optimizer import AdaptiveOptimizer, TaskSpec
    from armature.budget.planner import RequestPlanner

    plan_path = Path(preplan_file)
    if not plan_path.exists():
        console.print(f"[red]Build plan not found: {preplan_file}[/red]")
        return

    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    spec_id = plan_data.get("spec_id", "UNKNOWN")
    tasks = [
        TaskSpec(
            task_id=t["task_id"],
            description=t.get("description", ""),
            context_files=t.get("context_files", []),
            spec_refs=t.get("spec_refs", []),
            output_files=t.get("output_files", []),
            verify_command=t.get("verify_command", ""),
            phase=t.get("phase", "build"),
        )
        for t in plan_data.get("tasks", [])
    ]

    if not tasks:
        console.print("[yellow]No tasks found in build plan[/yellow]")
        return

    # Budget pre-plan: uniform allocation
    optimizer = AdaptiveOptimizer(config.budget)
    budget_plan = optimizer.plan_build(spec_id, tasks, complexity)

    # Request pre-plan: batching for all tasks
    planner = RequestPlanner()
    request_plan = planner.plan_build(spec_id, tasks)

    if json_output:
        output = {
            "spec_id": budget_plan.spec_id,
            "strategy": budget_plan.strategy,
            "feasible": budget_plan.feasible,
            "total_budget_tokens": budget_plan.total_budget_tokens,
            "total_estimated_tokens": budget_plan.total_estimated_tokens,
            "budget_utilization_pct": round(budget_plan.budget_utilization_pct, 1),
            "reserve_pct": budget_plan.reserve_pct,
            "optimizations": [
                {"strategy": o.strategy, "description": o.description,
                 "savings_pct": o.estimated_savings_pct}
                for o in budget_plan.optimizations
            ],
            "task_budgets": [
                {"task_id": tb.task_id, "max_input_tokens": tb.max_input_tokens,
                 "max_output_tokens": tb.max_output_tokens,
                 "optimization_applied": tb.optimization_applied,
                 "model": tb.model, "intent": tb.intent}
                for tb in budget_plan.task_budgets
            ],
            "execution_order": request_plan.execution_order,
            "warnings": budget_plan.warnings,
        }
        console.print(json.dumps(output, indent=2))
    else:
        print_header(f"Build Budget Plan: {spec_id}")
        console.print(optimizer.format_build_plan(budget_plan))
        console.print("")
        print_header("Request Batching Plan")
        console.print(planner.format_build_plan(request_plan))


def _handle_estimate(config, estimate_files: str, json_output: bool) -> None:
    """Estimate tokens for a set of files before sending to the LLM."""
    from armature.budget.optimizer import AdaptiveOptimizer

    optimizer = AdaptiveOptimizer(config.budget)
    files = [f.strip() for f in estimate_files.split(",")]
    estimate = optimizer.estimate_tokens(files)

    if json_output:
        console.print(json.dumps({
            "files": len(files),
            "input_tokens": estimate.input_tokens,
            "output_tokens": estimate.estimated_output_tokens,
            "total": estimate.total,
            "cost_usd": round(estimate.estimated_cost_usd, 4),
        }))
    else:
        print_header("Token Estimate")
        console.print(f"  Files: {len(files)}")
        console.print(f"  Context file tokens: {estimate.context_files_tokens:,}")
        console.print(f"  Estimated input total: {estimate.input_tokens:,}")
        console.print(f"  Estimated output: {estimate.estimated_output_tokens:,}")
        console.print(f"  Total (input + output): {estimate.total:,}")
        console.print(f"  Cacheable: {estimate.cacheable_pct:.0%}")
        console.print(f"  Estimated cost: ${estimate.estimated_cost_usd:.4f}")


def _handle_plan(plan_files: str, json_output: bool) -> None:
    """Plan optimal request batching for a set of files."""
    from armature.budget.planner import RequestPlanner, TaskContext

    planner = RequestPlanner()
    files = [f.strip() for f in plan_files.split(",")]
    task = TaskContext(context_files=files)
    plan = planner.plan_task(task, description="Batch analysis")

    print_header("Request Plan")
    console.print(planner.format_plan(plan))


def _handle_progress(config, tracker, spec_id: str, progress_file: str, complexity: str) -> None:
    """Check progress against a pre-plan."""
    from pathlib import Path

    from armature.budget.optimizer import AdaptiveOptimizer, TaskSpec

    plan_path = Path(progress_file)
    if not plan_path.exists():
        console.print(f"[red]Build plan not found: {progress_file}[/red]")
        return

    plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    tasks = [
        TaskSpec(
            task_id=t["task_id"],
            description=t.get("description", ""),
            context_files=t.get("context_files", []),
            spec_refs=t.get("spec_refs", []),
            phase=t.get("phase", "build"),
        )
        for t in plan_data.get("tasks", [])
    ]

    optimizer = AdaptiveOptimizer(config.budget)
    budget_plan = optimizer.plan_build(plan_data.get("spec_id", spec_id), tasks, complexity)

    # Get actual usage from tracker
    usage = tracker.get_usage(spec_id)
    actual_per_task: dict[str, int] = {}
    completed: list[str] = []

    # Build task-level actuals from JSONL entries with task_id field
    entries = tracker._load_entries(spec_id)
    for entry in entries:
        tid = entry.get("task_id", "")
        if tid:
            actual_per_task[tid] = actual_per_task.get(tid, 0) + entry.get("tokens", 0)

    # Mark tasks as completed if they have any logged usage
    for tb in budget_plan.task_budgets:
        if tb.task_id in actual_per_task:
            completed.append(tb.task_id)

    # Fallback: if no per-task data, estimate completion from total usage
    if not completed and usage["requests"] > 0:
        total_budget = budget_plan.total_budget_tokens
        if total_budget > 0:
            completion_ratio = min(1.0, usage["total_tokens"] / total_budget)
            estimated_done = int(len(budget_plan.task_budgets) * completion_ratio)
            for tb in budget_plan.task_budgets[:estimated_done]:
                completed.append(tb.task_id)

    progress = optimizer.check_task_progress(budget_plan, completed, actual_per_task)

    print_header(f"Budget Progress: {spec_id}")
    console.print(f"  Tasks completed: {progress['completed']} / {progress['completed'] + progress['remaining']}")
    console.print(f"  Tokens used:     {progress['total_actual_tokens']:,} / {progress['total_planned_tokens']:,}")
    console.print(f"  On track:        {'YES' if progress['on_track'] else 'NO'}")
    console.print(f"  Reserve used:    {progress['reserve_used']:,} / {progress['reserve_tokens']:,}")
    console.print(f"  Remaining task budgets unchanged: {progress['remaining_task_budgets_unchanged']}")

    if progress["overruns"]:
        console.print("\n  [yellow]Tasks over budget:[/yellow]")
        for o in progress["overruns"]:
            console.print(f"    {o['task_id']}: +{o['delta']:,} tokens over plan")

    if progress["savings"]:
        console.print("\n  [green]Tasks under budget:[/green]")
        for s in progress["savings"]:
            console.print(f"    {s['task_id']}: {abs(s['delta']):,} tokens saved")


def _handle_calibrate(config, spec_id: str) -> None:
    """Calibrate multipliers from a completed spec."""
    from armature.budget.calibrator import CalibrationStore, calibrate_from_spec
    from armature.budget.tracker import SessionTracker

    tracker = SessionTracker(config.budget)
    usage = tracker.get_usage(spec_id)
    if usage["requests"] == 0:
        console.print(f"[yellow]No usage data for {spec_id} -- nothing to calibrate from.[/yellow]")
        return

    from pathlib import Path

    from armature.budget.benchmark import calculate_benchmark, scan_project
    root = Path.cwd()
    scope = scan_project(root, config)
    benchmark = calculate_benchmark(scope)

    store = CalibrationStore(root / config.budget.storage)
    profile = calibrate_from_spec(spec_id, tracker, benchmark, store)

    print_header(f"Calibration: {spec_id}")
    console.print(f"  Specs calibrated:  {profile.specs_calibrated}")
    console.print(f"  Confidence:        {profile.confidence:.2f}")
    console.print(f"  Last calibrated:   {profile.last_calibrated}")

    console.print("\n  Task adjustments (actual/predicted ratio):")
    for task_type, adj in sorted(profile.task_adjustments.items()):
        direction = "high" if adj > 1.0 else "low"
        pct = abs(adj - 1.0) * 100
        console.print(f"    {task_type:<15} {adj:.2f}  (predictions were {pct:.0f}% too {direction})")

    console.print("\n  Model verbosity:")
    for model, mult in sorted(profile.model_verbosity.items()):
        console.print(f"    {model:<15} {mult:.2f}")

    console.print(f"\n  Cache hit rate:    {profile.cache_hit_rate:.2f}")


def _handle_calibration_status(config) -> None:
    """Show current calibration profile."""
    from pathlib import Path

    from armature.budget.calibrator import CalibrationStore

    root = Path.cwd()
    store = CalibrationStore(root / config.budget.storage)
    profile = store.load()

    if profile.specs_calibrated == 0:
        console.print("[yellow]No calibration data yet. Complete specs to build a profile.[/yellow]")
        console.print(f"  Min specs required: {config.budget.calibration.min_specs}")
        return

    print_header("Calibration Profile")
    console.print(f"  Specs calibrated:  {profile.specs_calibrated}")
    console.print(f"  Confidence:        {profile.confidence:.2f}")
    console.print(f"  Last calibrated:   {profile.last_calibrated}")

    console.print("\n  Task adjustments:")
    for task_type, adj in sorted(profile.task_adjustments.items()):
        console.print(f"    {task_type:<15} {adj:.2f}")

    console.print("\n  Model verbosity:")
    for model, mult in sorted(profile.model_verbosity.items()):
        console.print(f"    {model:<15} {mult:.2f}")

    console.print(f"\n  Cache hit rate:    {profile.cache_hit_rate:.2f}")

    # Show overrides from config
    overrides = config.budget.calibration
    if overrides.task_overrides or overrides.model_verbosity_overrides or overrides.cache_hit_rate_override is not None:
        console.print("\n  [yellow]Manual overrides (armature.yaml):[/yellow]")
        for k, v in overrides.task_overrides.items():
            console.print(f"    task: {k} = {v}")
        for k, v in overrides.model_verbosity_overrides.items():
            console.print(f"    model: {k} = {v}")
        if overrides.cache_hit_rate_override is not None:
            console.print(f"    cache_hit_rate = {overrides.cache_hit_rate_override}")


def _handle_industry_report(config, tracker, spec_id: str, model: str) -> None:
    """Show industry benchmark comparison for a spec's actual usage."""
    from pathlib import Path

    from armature.budget.benchmark import calculate_benchmark, scan_project
    from armature.budget.calibrator import compare_against_industry, format_industry_comparison

    root = Path.cwd()
    scope = scan_project(root, config)
    benchmark = calculate_benchmark(scope, model)
    comparison = compare_against_industry(benchmark, tracker, spec_id)

    console.print("")
    console.print(format_industry_comparison(comparison))


def _handle_cache_stats(tracker, spec_id: str) -> None:
    """Show semantic cache statistics for a spec."""
    stats = tracker.get_semantic_cache_stats(spec_id)
    print_header(f"Semantic Cache Stats: {spec_id}")
    console.print(f"  Total requests:  {stats['total_requests']}")
    console.print(f"  Cache hits:      {stats['cache_hits']}")
    console.print(f"  Cache misses:    {stats['cache_misses']}")
    console.print(f"  Hit rate:        {stats['hit_rate']:.0%}")
    console.print(f"  Tokens saved:    {stats['tokens_saved']:,}")
