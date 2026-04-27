"""Benchmark result formatting for CLI, JSON, and publishable reports."""

from __future__ import annotations

from typing import Any

from armature._internal.types import AgentArenaResult, CorrelationResult


class BenchmarkReporter:
    """Format benchmark results for various output targets."""

    def format_arena_results(self, results: list[AgentArenaResult]) -> str:
        """Format arena comparison as ASCII table."""
        lines: list[str] = []
        lines.append("ARMATURE AGENT ARENA — BENCHMARK RESULTS")
        lines.append("=" * 72)
        lines.append("")

        # Overall ranking table
        lines.append(f"  {'Agent':<15} {'Quality':>8} {'Budget':>10} {'Heal':>6} "
                      f"{'Cache':>6} {'SCORE':>7} {'Grade':>6}")
        lines.append(f"  {'-' * 64}")

        for r in results:
            total_cost = sum(t.budget_cost_usd for t in r.task_results)
            cost_str = f"${total_cost:.2f}" if total_cost > 0 else "$0.00"
            lines.append(
                f"  {r.agent:<15} {r.quality_avg:>7.1f}% {cost_str:>10} "
                f"{r.heal_rate:>5.0%} {r.cache_hit_rate:>5.0%} "
                f"{r.composite_score:>6.1f} {r.grade:>6}"
            )

        lines.append("")

        # Pass rate
        lines.append("  TASK COMPLETION")
        lines.append(f"  {'-' * 40}")
        for r in results:
            passed = sum(1 for t in r.task_results if t.passed)
            total = len(r.task_results)
            pct = (passed / total * 100) if total > 0 else 0
            lines.append(f"  {r.agent:<15} {passed}/{total} ({pct:.0f}%)")

        lines.append("")

        # Token usage
        lines.append("  TOKEN USAGE")
        lines.append(f"  {'-' * 40}")
        for r in results:
            total_tokens = sum(t.budget_tokens for t in r.task_results)
            avg_tokens = total_tokens // len(r.task_results) if r.task_results else 0
            lines.append(f"  {r.agent:<15} {total_tokens:>10,} total, {avg_tokens:>8,} avg/task")

        return "\n".join(lines)

    def format_correlation_report(self, result: CorrelationResult) -> str:
        """Format SWE-bench correlation analysis."""
        lines: list[str] = []
        lines.append("ARMATURE QUALITY SCORE — CORRECTNESS CORRELATION")
        lines.append("=" * 60)
        lines.append("")

        lines.append("  STATISTICAL MEASURES")
        lines.append(f"  {'-' * 50}")
        lines.append(f"  Pearson r:           {result.pearson_r:>8.4f}")
        lines.append(f"  Spearman rho:        {result.spearman_rho:>8.4f}")
        lines.append(f"  p-value:             {result.p_value:>8.6f}")
        if result.p_value < 0.001:
            sig = "***"
        elif result.p_value < 0.01:
            sig = "**"
        elif result.p_value < 0.05:
            sig = "*"
        else:
            sig = "n.s."
        lines.append(f"  Significance:        {sig:>8}")
        lines.append("")

        lines.append("  CLASSIFICATION PERFORMANCE")
        lines.append(f"  {'-' * 50}")
        lines.append(f"  ROC-AUC:             {result.roc_auc:>8.4f}")
        lines.append(f"  Optimal threshold:   {result.optimal_threshold:>7.1f}%")
        lines.append("")

        if result.quality_bands:
            lines.append("  QUALITY BANDS → PASS RATE")
            lines.append(f"  {'-' * 50}")
            lines.append(f"  {'Band':<12} {'Pass Rate':>10} {'N':>6}")
            for band in result.quality_bands:
                n = int(band.get("n", 0))
                if n > 0:
                    rate = float(band.get("pass_rate", 0.0))
                    lines.append(f"  {band['band']:<12} {rate:>9.0%} {n:>6}")

        if result.per_check_importance:
            lines.append("")
            lines.append("  PER-CHECK IMPORTANCE (correlation with pass/fail)")
            lines.append(f"  {'-' * 50}")
            for check, importance in result.per_check_importance.items():
                bar = "█" * int(importance * 20)
                lines.append(f"  {check:<20} {importance:>5.3f}  {bar}")

        return "\n".join(lines)

    def format_per_task_breakdown(
        self,
        results: list[AgentArenaResult],
    ) -> str:
        """Per-task-type breakdown: Best Agent per category."""
        from armature.benchmark.scoring import compute_per_category_rankings

        rankings = compute_per_category_rankings(results)
        lines: list[str] = []
        lines.append("  PER-CATEGORY RANKINGS")
        lines.append(f"  {'-' * 50}")
        lines.append(f"  {'Category':<15} {'Best Quality':<18} {'Best Cost':<18}")
        lines.append(f"  {'-' * 50}")

        for cat in ["bugfix", "feature", "refactor", "test_gen", "documentation"]:
            r = rankings.get(cat, {})
            lines.append(
                f"  {cat:<15} {r.get('best_quality', '-'):<18} "
                f"{r.get('best_cost', '-'):<18}"
            )

        return "\n".join(lines)

    def export_json(
        self,
        arena_results: list[AgentArenaResult] | None = None,
        correlation_result: CorrelationResult | None = None,
    ) -> dict[str, Any]:
        """Export all results as JSON-serializable dict."""
        output: dict[str, Any] = {}

        if arena_results:
            output["arena"] = {
                "agents": [
                    {
                        "agent": r.agent,
                        "composite_score": r.composite_score,
                        "grade": r.grade,
                        "quality_avg": r.quality_avg,
                        "efficiency_score": r.efficiency_score,
                        "heal_rate": r.heal_rate,
                        "cache_hit_rate": r.cache_hit_rate,
                        "tasks_passed": sum(1 for t in r.task_results if t.passed),
                        "tasks_total": len(r.task_results),
                        "total_tokens": sum(t.budget_tokens for t in r.task_results),
                        "total_cost_usd": round(sum(t.budget_cost_usd for t in r.task_results), 4),
                    }
                    for r in arena_results
                ]
            }

        if correlation_result:
            output["correlation"] = {
                "pearson_r": correlation_result.pearson_r,
                "spearman_rho": correlation_result.spearman_rho,
                "p_value": correlation_result.p_value,
                "roc_auc": correlation_result.roc_auc,
                "optimal_threshold": correlation_result.optimal_threshold,
                "per_check_importance": correlation_result.per_check_importance,
                "quality_bands": correlation_result.quality_bands,
            }

        return output
