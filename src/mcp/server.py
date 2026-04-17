"""Armature MCP Server -- exposes harness tools to Claude Code.

This implements a Model Context Protocol server so Armature's capabilities
can be used as tools directly within Claude Code conversations.

Usage:
    python -m armature.mcp.server          # stdio transport
    armature mcp-server                     # via CLI entry point
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# MCP server protocol (simplified -- follows Claude Code MCP spec)
# Full MCP SDK integration would use `mcp` package when available


def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle an MCP tool call and return results."""
    handlers = {
        "armature_check": _tool_check,
        "armature_heal": _tool_heal,
        "armature_gc": _tool_gc,
        "armature_budget": _tool_budget,
        "armature_preplan": _tool_preplan,
        "armature_benchmark": _tool_benchmark,
        "armature_estimate": _tool_estimate,
        "armature_baseline": _tool_baseline,
        "armature_pre_dev": _tool_pre_dev,
        "armature_post_dev": _tool_post_dev,
        "armature_route": _tool_route,
        "armature_calibrate": _tool_calibrate,
        "armature_cache_stats": _tool_cache_stats,
    }

    handler = handlers.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}

    return handler(arguments)


def get_tool_definitions() -> list[dict]:
    """Return MCP tool definitions for Armature capabilities."""
    return [
        {
            "name": "armature_check",
            "description": "Run quality sensors (lint, type check, architecture, conformance). "
                           "Returns quality score and violations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "Check a single file (optional)"},
                },
            },
        },
        {
            "name": "armature_heal",
            "description": "Self-healing pipeline: auto-fix lint violations, report type/test errors. "
                           "Uses circuit breaker (max 3 attempts per failure type).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "failures": {"type": "string", "default": "lint,type,test",
                                 "description": "Comma-separated failure types"},
                    "spec_id": {"type": "string", "default": "UNKNOWN"},
                },
            },
        },
        {
            "name": "armature_gc",
            "description": "Run garbage collection agents: architecture drift, stale docs, dead code, budget audit.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Specific agent to run (optional)"},
                },
            },
        },
        {
            "name": "armature_budget",
            "description": "Track or report development session costs per spec/phase.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["log", "report"]},
                    "spec_id": {"type": "string"},
                    "phase": {"type": "string"},
                    "tokens": {"type": "integer"},
                    "cost_usd": {"type": "number"},
                },
                "required": ["action", "spec_id"],
            },
        },
        {
            "name": "armature_preplan",
            "description": "Pre-plan budget for an ENTIRE build upfront. Estimates all tasks, "
                           "picks ONE uniform strategy, allocates equal per-task budgets. "
                           "Every task -- first and last -- gets the same quality context. "
                           "No progressive degradation.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec_id": {"type": "string", "description": "Spec ID"},
                    "tasks": {
                        "type": "array",
                        "description": "All tasks in the build plan",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string"},
                                "description": {"type": "string"},
                                "context_files": {"type": "array", "items": {"type": "string"}},
                                "spec_refs": {"type": "array", "items": {"type": "string"}},
                                "output_files": {"type": "array", "items": {"type": "string"}},
                                "verify_command": {"type": "string"},
                                "phase": {"type": "string", "default": "build"},
                            },
                            "required": ["task_id"],
                        },
                    },
                    "complexity": {"type": "string", "default": "medium",
                                   "description": "Budget tier (low/medium/high/critical)"},
                },
                "required": ["spec_id", "tasks"],
            },
        },
        {
            "name": "armature_benchmark",
            "description": "Scan project scope (LOC, files, architecture) and check if budget "
                           "tiers are right-sized. Warns if budget is too low (quality suffers) "
                           "or too high (wasteful). Returns per-task-type cost estimates. "
                           "Set include_industry=true to compare against SWE-bench/DevBench targets.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "complexity": {"type": "string", "default": "medium",
                                   "description": "Budget tier to check (low/medium/high/critical)"},
                    "model": {"type": "string", "default": "sonnet",
                              "description": "Model for cost estimation (sonnet/opus/haiku)"},
                    "include_industry": {"type": "boolean", "default": False,
                                         "description": "Include industry benchmark comparison"},
                },
            },
        },
        {
            "name": "armature_estimate",
            "description": "Estimate token count for a set of files before sending to the LLM. "
                           "Use to pre-size requests and avoid budget overruns.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"},
                              "description": "File paths to estimate tokens for"},
                    "model": {"type": "string", "default": "sonnet",
                              "description": "Model to estimate cost for (sonnet/opus/haiku)"},
                },
                "required": ["files"],
            },
        },
        {
            "name": "armature_baseline",
            "description": "Capture or compare quality baselines for regression detection.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["capture", "compare"]},
                    "spec_id": {"type": "string"},
                },
                "required": ["action", "spec_id"],
            },
        },
        {
            "name": "armature_pre_dev",
            "description": "Pre-development checks: environment validation, spec readiness, baseline capture.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec_id": {"type": "string"},
                    "env_check_only": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "armature_post_dev",
            "description": "Post-development checks: regression detection against baseline.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec_id": {"type": "string"},
                },
                "required": ["spec_id"],
            },
        },
        {
            "name": "armature_route",
            "description": "Route a task to the cheapest adequate model based on intent "
                           "and quality floor. Returns model name, cost estimate, and alternatives.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string",
                               "description": "Task intent: code_gen, complex_code_gen, explain, "
                                              "test_gen, research, lint_fix, reasoning"},
                    "estimated_input": {"type": "integer", "default": 10000},
                    "estimated_output": {"type": "integer", "default": 4000},
                },
                "required": ["intent"],
            },
        },
        {
            "name": "armature_calibrate",
            "description": "Calibrate budget multipliers from a completed spec. Compares "
                           "actual usage vs benchmark predictions and updates the calibration "
                           "profile using exponential moving average.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec_id": {"type": "string", "description": "Completed spec ID to calibrate from"},
                    "action": {"type": "string", "enum": ["calibrate", "status"],
                               "default": "calibrate"},
                },
                "required": ["spec_id"],
            },
        },
        {
            "name": "armature_cache_stats",
            "description": "Get semantic cache statistics: hit rate, tokens saved, entries by intent.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "spec_id": {"type": "string", "description": "Spec ID for per-spec stats (optional)"},
                },
            },
        },
    ]


def _tool_check(args: dict) -> dict:
    """Run quality checks."""
    from armature.config.loader import load_config_or_defaults
    from armature.quality.scorer import run_quality_checks

    config = load_config_or_defaults()
    root = Path.cwd()
    results = run_quality_checks(config.quality, root, file_path=args.get("file"))
    return {
        "checks": [{"name": r.name, "passed": r.passed, "violations": r.violation_count, "details": r.details}
                    for r in results],
        "score": sum(r.score for r in results) / len(results) if results else 1.0,
    }


def _tool_heal(args: dict) -> dict:
    """Run self-healing pipeline."""
    from armature.config.loader import load_config_or_defaults
    from armature.heal.pipeline import HealPipeline

    config = load_config_or_defaults()
    pipeline = HealPipeline(config.heal)
    failure_types = set(args.get("failures", "lint,type,test").split(","))
    results = pipeline.heal(failure_types)
    return {
        "results": [{"type": r.failure_type, "fixed": r.fixed, "details": r.details} for r in results],
        "all_fixed": all(r.fixed for r in results),
    }


def _tool_gc(args: dict) -> dict:
    """Run GC agents."""
    from armature.config.loader import load_config_or_defaults
    from armature.gc.runner import GCRunner

    config = load_config_or_defaults()
    runner = GCRunner(config.gc, config)
    findings = runner.run(agent_name=args.get("agent"))
    return {
        "findings": [{"agent": f.agent, "category": f.category, "file": f.file, "message": f.message}
                     for f in findings],
        "total": len(findings),
    }


def _tool_budget(args: dict) -> dict:
    """Track or report budget."""
    from armature.budget.tracker import SessionTracker
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    tracker = SessionTracker(config.budget)

    if args["action"] == "log":
        tracker.log(args["spec_id"], args.get("phase", ""), args.get("tokens", 0), args.get("cost_usd", 0.0))
        return {"logged": True}
    else:
        usage = tracker.get_usage(args["spec_id"])
        suggestions = tracker.get_optimization_suggestions(args["spec_id"])
        return {**usage, "suggestions": suggestions}


def _tool_preplan(args: dict) -> dict:
    """Pre-plan budget for an entire build -- uniform allocation."""
    from armature.budget.optimizer import AdaptiveOptimizer, TaskSpec
    from armature.budget.planner import RequestPlanner
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    if not config.budget.enabled:
        return {"error": "Budget tracking is disabled"}

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
        for t in args.get("tasks", [])
    ]

    complexity = args.get("complexity", "medium")
    optimizer = AdaptiveOptimizer(config.budget)
    budget_plan = optimizer.plan_build(args["spec_id"], tasks, complexity)

    planner = RequestPlanner()
    request_plan = planner.plan_build(args["spec_id"], tasks)

    return {
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
        "total_request_savings": request_plan.total_savings,
        "shared_context_files": request_plan.shared_context_files,
        "warnings": budget_plan.warnings,
    }


def _tool_benchmark(args: dict) -> dict:
    """Scan project scope and check budget fit."""
    from armature.budget.benchmark import scan_project, calculate_benchmark, check_budget_fit
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    root = Path.cwd()
    complexity = args.get("complexity", "medium")
    model = args.get("model", "sonnet")

    scope = scan_project(root, config)
    benchmark = calculate_benchmark(scope, model)

    result: dict = {
        "scope": {
            "language": scope.language,
            "framework": scope.framework,
            "source_files": scope.total_source_files,
            "loc": scope.total_loc,
            "test_files": scope.total_test_files,
            "architectural_layers": scope.architectural_layers,
        },
        "benchmarks": {
            task_type: {"tokens": est.estimated_tokens, "cost_usd": est.estimated_cost_usd}
            for task_type, est in benchmark.estimates.items()
        },
        "recommended_tier": benchmark.recommended_tier,
        "recommended_tokens": benchmark.recommended_tokens,
    }

    if config.budget.enabled:
        warning = check_budget_fit(config.budget, scope, complexity, model)
        result["budget_fit"] = {
            "level": warning.level,
            "message": warning.message,
            "configured_tokens": warning.configured_tokens,
            "benchmark_tokens": warning.benchmark_tokens,
            "recommended_tier": warning.recommended_tier,
        }

    if args.get("include_industry"):
        from armature.budget.calibrator import compare_against_industry, assess_quality_budget_position
        from armature.budget.tracker import SessionTracker

        if config.budget.enabled:
            tracker = SessionTracker(config.budget)
            specs = tracker.list_specs()
            spec_id = specs[-1] if specs else ""
            comparison = compare_against_industry(benchmark, tracker, spec_id)
        else:
            # Benchmark-only comparison without actual usage data
            from armature.budget.calibrator import (
                IndustryComparison, INDUSTRY_TASK_TARGETS, INDUSTRY_PHASE_TARGETS,
                compute_efficiency_grades,
            )
            quality_pct, quality_note = assess_quality_budget_position(benchmark.recommended_tokens)
            task_positions = {}
            for task_type, targets in INDUSTRY_TASK_TARGETS.items():
                est = benchmark.estimates.get(task_type)
                actual = est.estimated_tokens if est else 0
                task_positions[task_type] = {
                    "actual": actual, "p25": targets["p25"],
                    "median": targets["median"], "p75": targets["p75"],
                }

            comparison = IndustryComparison(
                task_positions=task_positions,
                budget_tokens=benchmark.recommended_tokens,
                estimated_quality_pct=quality_pct,
                quality_ceiling_note=quality_note,
                cost_per_loc=None, cache_hit_rate=0.0,
                routing_savings_ratio=None, calibration_drift=None,
                phase_comparison={}, grades={},
            )
            comparison.grades = compute_efficiency_grades(comparison)

        result["industry_comparison"] = {
            "task_positions": comparison.task_positions,
            "budget_tokens": comparison.budget_tokens,
            "estimated_quality_pct": comparison.estimated_quality_pct,
            "quality_ceiling_note": comparison.quality_ceiling_note,
            "grades": comparison.grades,
            "phase_comparison": comparison.phase_comparison,
        }

    return result


def _tool_estimate(args: dict) -> dict:
    """Estimate tokens for files."""
    from armature.budget.optimizer import AdaptiveOptimizer
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    optimizer = AdaptiveOptimizer(config.budget)
    estimate = optimizer.estimate_tokens(
        context_files=args["files"],
        model=args.get("model", "sonnet"),
    )
    return {
        "input_tokens": estimate.input_tokens,
        "estimated_output_tokens": estimate.estimated_output_tokens,
        "total": estimate.total,
        "context_files_tokens": estimate.context_files_tokens,
        "cacheable_pct": estimate.cacheable_pct,
        "estimated_cost_usd": estimate.estimated_cost_usd,
    }


def _tool_baseline(args: dict) -> dict:
    """Capture or compare baseline."""
    from armature.config.loader import load_config_or_defaults
    from armature.gc.baseline import BaselineManager
    from armature.quality.scorer import capture_baseline_snapshot

    config = load_config_or_defaults()
    root = Path.cwd()
    manager = BaselineManager(root / ".armature" / "baselines")

    if args["action"] == "capture":
        snapshot = capture_baseline_snapshot(config.quality, root)
        path = manager.save(args["spec_id"], snapshot)
        return {"saved": str(path), "lint": snapshot.lint_violations, "type_errors": snapshot.type_errors}
    else:
        baseline = manager.load(args["spec_id"])
        if baseline is None:
            return {"error": f"No baseline for {args['spec_id']}"}
        current = capture_baseline_snapshot(config.quality, root)
        diff = manager.diff(baseline, current)
        return diff


def _tool_pre_dev(args: dict) -> dict:
    """Run pre-dev checks: environment validation, spec readiness, baseline capture."""
    import shutil
    import sys
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    root = Path.cwd()

    # Environment checks
    checks = []
    py_ok = sys.version_info >= (3, 11)
    checks.append({"name": "python", "ok": py_ok, "value": sys.version.split()[0]})
    for tool in ["ruff", "mypy", "pytest"]:
        checks.append({"name": tool, "ok": bool(shutil.which(tool)),
                        "value": shutil.which(tool) or "not found"})

    env_ok = all(c["ok"] for c in checks)

    if args.get("env_check_only"):
        return {"environment": checks, "all_ok": env_ok}

    spec_id = args.get("spec_id")
    result: dict = {"environment": checks, "all_ok": env_ok}

    if spec_id:
        from armature.gc.baseline import BaselineManager
        from armature.quality.scorer import capture_baseline_snapshot
        snapshot = capture_baseline_snapshot(config.quality, root)
        manager = BaselineManager(root / ".armature" / "baselines")
        path = manager.save(spec_id, snapshot)
        result["baseline"] = {
            "spec_id": spec_id,
            "lint_violations": snapshot.lint_violations,
            "type_errors": snapshot.type_errors,
            "test_passed": snapshot.test_passed,
            "test_failed": snapshot.test_failed,
            "saved_to": str(path),
        }

    return result


def _tool_post_dev(args: dict) -> dict:
    """Run post-dev checks: regression detection against baseline."""
    from armature.config.loader import load_config_or_defaults
    from armature.gc.baseline import BaselineManager
    from armature.quality.scorer import capture_baseline_snapshot

    config = load_config_or_defaults()
    root = Path.cwd()
    spec_id = args["spec_id"]

    manager = BaselineManager(root / ".armature" / "baselines")
    baseline = manager.load(spec_id)
    if baseline is None:
        return {"error": f"No baseline found for {spec_id}. Run pre-dev first."}

    current = capture_baseline_snapshot(config.quality, root)
    diff = manager.diff(baseline, current)

    result: dict = {
        "spec_id": spec_id,
        "regression": diff,
        "baseline": {
            "lint_violations": baseline.lint_violations,
            "type_errors": baseline.type_errors,
            "test_passed": baseline.test_passed,
            "test_failed": baseline.test_failed,
        },
        "current": {
            "lint_violations": current.lint_violations,
            "type_errors": current.type_errors,
            "test_passed": current.test_passed,
            "test_failed": current.test_failed,
        },
    }

    # Architecture checks
    if config.architecture.enabled:
        from armature.architecture.boundary import run_boundary_check
        from armature.architecture.conformance import run_conformance_check
        boundary = run_boundary_check(config.architecture, root)
        conform = run_conformance_check(config.architecture, root)
        result["architecture"] = {
            "boundary_passed": boundary.passed,
            "boundary_violations": boundary.violation_count,
            "conformance_passed": conform.passed,
            "conformance_violations": conform.violation_count,
        }

    result["passed"] = not diff["has_regression"]
    return result


def _tool_route(args: dict) -> dict:
    """Route a task to the cheapest adequate model."""
    from armature.budget.router import ModelRouter
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    router = ModelRouter(
        enabled_models=config.budget.providers.enabled_models,
        quality_floor=config.budget.providers.quality_floor,
        premium_intents=config.budget.providers.premium_intents,
    )
    decision = router.route(
        args["intent"],
        args.get("estimated_input", 10_000),
        args.get("estimated_output", 4_000),
    )
    comparison = router.compare_models(
        args["intent"],
        args.get("estimated_input", 10_000),
        args.get("estimated_output", 4_000),
    )
    return {
        "model": decision.model,
        "reason": decision.reason,
        "estimated_cost_usd": decision.estimated_cost_usd,
        "alternative": decision.alternative,
        "all_options": comparison,
    }


def _tool_calibrate(args: dict) -> dict:
    """Calibrate multipliers from a completed spec or show status."""
    from armature.budget.calibrator import CalibrationStore, calibrate_from_spec, apply_calibration
    from armature.budget.benchmark import scan_project, calculate_benchmark
    from armature.budget.tracker import SessionTracker
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    root = Path.cwd()
    store = CalibrationStore(root / config.budget.storage)

    action = args.get("action", "calibrate")
    if action == "status":
        profile = store.load()
        effective = apply_calibration(profile)
        return {
            "specs_calibrated": profile.specs_calibrated,
            "confidence": profile.confidence,
            "last_calibrated": profile.last_calibrated,
            "task_adjustments": profile.task_adjustments,
            "model_verbosity": profile.model_verbosity,
            "cache_hit_rate": profile.cache_hit_rate,
            "effective_multipliers": effective,
        }

    spec_id = args.get("spec_id", "")
    if not spec_id:
        return {"error": "spec_id required for calibration"}

    tracker = SessionTracker(config.budget)
    scope = scan_project(root, config)
    benchmark = calculate_benchmark(scope)
    profile = calibrate_from_spec(spec_id, tracker, benchmark, store)

    return {
        "calibrated": True,
        "spec_id": spec_id,
        "specs_calibrated": profile.specs_calibrated,
        "confidence": profile.confidence,
        "task_adjustments": profile.task_adjustments,
        "cache_hit_rate": profile.cache_hit_rate,
    }


def _tool_cache_stats(args: dict) -> dict:
    """Get semantic cache statistics."""
    from armature.budget.cache import SemanticCache
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    root = Path.cwd()
    cache = SemanticCache(
        storage_dir=root / config.budget.cache.storage,
        max_size_mb=config.budget.cache.max_size_mb,
        ttl_days=config.budget.cache.ttl_days,
        root=root,
    )

    stats = cache.stats()

    # Add per-spec stats if spec_id provided
    spec_id = args.get("spec_id")
    if spec_id:
        from armature.budget.tracker import SessionTracker
        tracker = SessionTracker(config.budget)
        spec_stats = tracker.get_semantic_cache_stats(spec_id)
        stats["spec"] = spec_stats

    return stats
