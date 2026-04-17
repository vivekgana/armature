"""Comparison engine: run armature quality checks on ossature-generated output."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from armature._internal.types import CheckResult
from armature.compat._ossature_model import load_ossature_project
from armature.compat.ossature import ConversionWarning, convert_ossature_project
from armature.config.schema import ArmatureConfig


@dataclass
class ComparisonReport:
    ossature_project_name: str = ""
    ossature_language: str = ""
    ossature_output_dir: str = ""

    quality_results: list[CheckResult] = field(default_factory=list)
    quality_score: float = 0.0
    quality_level: str = "draft"

    budget_tier: str = "medium"
    budget_estimate_tokens: int = 0
    budget_estimate_cost_usd: float = 0.0

    architecture_enabled: bool = False
    layer_count: int = 0
    boundary_count: int = 0
    boundary_violations: int = 0

    spec_count: int = 0
    spec_ids: list[str] = field(default_factory=list)

    unsupported_language: bool = False
    unsupported_tools: list[str] = field(default_factory=list)
    conversion_warnings: list[ConversionWarning] = field(default_factory=list)

    output_dir_exists: bool = True


def compare_ossature_project(
    ossature_root: Path,
    *,
    armature_config: ArmatureConfig | None = None,
    output_dir: Path | None = None,
) -> ComparisonReport:
    """Run armature quality governance on an ossature project's output."""
    ossature = load_ossature_project(ossature_root)
    conversion = convert_ossature_project(ossature_root)
    config = armature_config or conversion.config

    effective_output = output_dir or (ossature_root / ossature.output.dir)

    report = ComparisonReport(
        ossature_project_name=ossature.project.name,
        ossature_language=ossature.output.language,
        ossature_output_dir=str(effective_output),
        budget_tier=_infer_tier(conversion),
        spec_count=len(ossature.specs),
        spec_ids=[s.id for s in ossature.specs if s.id],
        conversion_warnings=conversion.warnings,
        unsupported_language=any(w.field == "project.language" for w in conversion.warnings),
        unsupported_tools=[w.ossature_value for w in conversion.warnings if "tool" in w.field.lower()],
    )

    if config.architecture.enabled:
        report.architecture_enabled = True
        report.layer_count = len(config.architecture.layers)
        report.boundary_count = len(config.architecture.boundaries)

    if not effective_output.is_dir():
        report.output_dir_exists = False
        return report

    if config.quality.enabled:
        try:
            from armature.quality.scorer import run_quality_checks
            results = run_quality_checks(config.quality, effective_output)
            report.quality_results = results
            report.quality_score = _weighted_score(results, config)
            report.quality_level = _determine_level(report.quality_score, config)
        except Exception:
            pass

    if config.architecture.enabled and effective_output.is_dir():
        try:
            from armature.architecture.boundary import run_boundary_check
            boundary_result = run_boundary_check(config.architecture, effective_output)
            report.boundary_violations = boundary_result.violation_count
        except Exception:
            pass

    if config.budget.enabled:
        report.budget_estimate_tokens = config.budget.defaults.get(
            report.budget_tier, config.budget.defaults.get("medium")
        ).max_tokens
        report.budget_estimate_cost_usd = config.budget.defaults.get(
            report.budget_tier, config.budget.defaults.get("medium")
        ).max_cost_usd

    return report


def _infer_tier(conversion) -> str:
    """Extract the inferred budget tier from a conversion."""
    from armature.compat.ossature import _infer_model_tier
    if conversion.ossature_project and conversion.ossature_project.llm.model:
        return _infer_model_tier(conversion.ossature_project.llm.model)
    return "medium"


def _weighted_score(results: list[CheckResult], config: ArmatureConfig) -> float:
    """Calculate weighted quality score from check results."""
    if not results:
        return 0.0
    total_weight = 0
    weighted_sum = 0.0
    for r in results:
        check_cfg = config.quality.checks.get(r.name)
        weight = check_cfg.weight if check_cfg else 25
        weighted_sum += r.score * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _determine_level(score: float, config: ArmatureConfig) -> str:
    """Determine quality level from score and gate thresholds."""
    gates = config.quality.gates
    if score >= gates.get("merge_ready", 0.95):
        return "merge_ready"
    if score >= gates.get("review_ready", 0.85):
        return "review_ready"
    return "draft"


def format_comparison_report(report: ComparisonReport) -> str:
    """Format a ComparisonReport as human-readable text."""
    lines = [
        f"Ossature-Armature Comparison: {report.ossature_project_name}",
        "=" * 60,
        "",
        f"  Language:    {report.ossature_language}" + (" (unsupported)" if report.unsupported_language else ""),
        f"  Output dir:  {report.ossature_output_dir}" + ("" if report.output_dir_exists else " (NOT FOUND)"),
        f"  Specs:       {report.spec_count} ({', '.join(report.spec_ids) or 'none'})",
        "",
        "Quality",
        "-" * 40,
        f"  Score:  {report.quality_score:.1%}",
        f"  Level:  {report.quality_level}",
    ]

    for r in report.quality_results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{status}] {r.name}: {r.details}")

    lines.extend([
        "",
        "Architecture",
        "-" * 40,
        f"  Enabled:     {report.architecture_enabled}",
        f"  Layers:      {report.layer_count}",
        f"  Boundaries:  {report.boundary_count}",
        f"  Violations:  {report.boundary_violations}",
        "",
        "Budget",
        "-" * 40,
        f"  Tier:            {report.budget_tier}",
        f"  Token estimate:  {report.budget_estimate_tokens:,}",
        f"  Cost estimate:   ${report.budget_estimate_cost_usd:.2f}",
    ])

    if report.conversion_warnings:
        lines.extend(["", "Warnings", "-" * 40])
        for w in report.conversion_warnings:
            lines.append(f"  [{w.field}] {w.reason}")

    return "\n".join(lines)


def comparison_report_to_dict(report: ComparisonReport) -> dict:
    """Convert ComparisonReport to a JSON-serializable dict."""
    d = asdict(report)
    d["conversion_warnings"] = [asdict(w) for w in report.conversion_warnings]
    d["quality_results"] = [asdict(r) for r in report.quality_results]
    return d
