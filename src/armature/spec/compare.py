"""Comparison engine — armature spec requirements vs ossature project capabilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from armature.compat._ossature_model import OssatureProjectFull, load_ossature_project
from armature.compat.compare import ComparisonReport, compare_ossature_project
from armature.config.schema import ArmatureConfig
from armature.spec.loader import SpecRecord, load_project_specs


@dataclass
class SpecRequirementsSummary:
    project_name: str
    project_language: str
    spec_count: int
    spec_ids: list[str]
    spec_types: dict[str, int]
    total_ac_count: int
    testable_ac_count: int
    max_coverage_min: int
    min_coverage_min: int
    avg_coverage_min: float
    integration_test_required_count: int
    e2e_test_required_count: int
    human_gate_count: int
    linting_enforced: bool
    type_check_enforced: bool
    budget_tier: str
    budget_max_tokens: int
    budget_max_cost_usd: float
    quality_gate_merge_ready: float
    quality_tools: list[str]
    architecture_layers: int
    architecture_boundaries: int


@dataclass
class OssatureCapabilitiesSummary:
    project_name: str
    project_language: str
    ossature_model: str
    budget_tier: str
    budget_estimate_tokens: int
    budget_estimate_cost_usd: float
    spec_count: int
    spec_ids: list[str]
    has_architecture_specs: bool
    architecture_component_count: int
    has_output_dir: bool
    quality_score: float
    quality_level: str
    quality_checks_passed: list[str]
    quality_checks_failed: list[str]
    unsupported_language: bool
    unsupported_tools: list[str]
    boundary_violations: int


@dataclass
class ComparisonDimension:
    dimension: str
    armature_value: str
    ossature_value: str
    gap: str  # MEETS, GAP, UNKNOWN, N/A
    notes: str = ""


@dataclass
class SpecComparisonReport:
    armature_project: str
    ossature_project: str
    pairing_rationale: str
    armature: SpecRequirementsSummary
    ossature: OssatureCapabilitiesSummary
    dimensions: list[ComparisonDimension]
    overall_gap_count: int = 0
    overall_meets_count: int = 0
    generated_at: str = ""


def build_armature_summary(
    config: ArmatureConfig, specs: list[SpecRecord]
) -> SpecRequirementsSummary:
    spec_types: dict[str, int] = {}
    for s in specs:
        spec_types[s.spec_type] = spec_types.get(s.spec_type, 0) + 1

    total_ac = sum(len(s.acceptance_criteria) for s in specs)
    testable_ac = sum(
        sum(1 for ac in s.acceptance_criteria if ac.testable) for s in specs
    )

    coverage_mins = [s.eval_requirements.unit_test_coverage_min for s in specs]
    max_cov = max(coverage_mins) if coverage_mins else 0
    min_cov = min(coverage_mins) if coverage_mins else 0
    avg_cov = sum(coverage_mins) / len(coverage_mins) if coverage_mins else 0.0

    integration_count = sum(
        1 for s in specs if s.eval_requirements.integration_test_required
    )
    e2e_count = sum(1 for s in specs if s.eval_requirements.e2e_test_required)
    gate_count = sum(len(s.human_gates) for s in specs)
    linting = any(s.eval_requirements.linting_must_pass for s in specs)
    type_check = any(s.eval_requirements.type_check_must_pass for s in specs)

    budget_tier = "medium"
    budget_tokens = 500_000
    budget_cost = 10.0
    if config.budget.enabled and "medium" in config.budget.defaults:
        tier = config.budget.defaults["medium"]
        budget_tokens = tier.max_tokens
        budget_cost = tier.max_cost_usd

    quality_tools = []
    if config.quality.enabled:
        for _check_name, check_cfg in config.quality.checks.items():
            if check_cfg.tool:
                quality_tools.append(check_cfg.tool)

    arch_layers = len(config.architecture.layers) if config.architecture.enabled else 0
    arch_bounds = (
        len(config.architecture.boundaries) if config.architecture.enabled else 0
    )

    return SpecRequirementsSummary(
        project_name=config.project.name,
        project_language=config.project.language,
        spec_count=len(specs),
        spec_ids=[s.spec_id for s in specs],
        spec_types=spec_types,
        total_ac_count=total_ac,
        testable_ac_count=testable_ac,
        max_coverage_min=max_cov,
        min_coverage_min=min_cov,
        avg_coverage_min=avg_cov,
        integration_test_required_count=integration_count,
        e2e_test_required_count=e2e_count,
        human_gate_count=gate_count,
        linting_enforced=linting,
        type_check_enforced=type_check,
        budget_tier=budget_tier,
        budget_max_tokens=budget_tokens,
        budget_max_cost_usd=budget_cost,
        quality_gate_merge_ready=config.quality.gates.get("merge_ready", 0.95),
        quality_tools=quality_tools,
        architecture_layers=arch_layers,
        architecture_boundaries=arch_bounds,
    )


def build_ossature_summary(
    report: ComparisonReport, ossature_project: OssatureProjectFull
) -> OssatureCapabilitiesSummary:
    passed = []
    failed = []
    for r in report.quality_results:
        if r.score >= 0.85:
            passed.append(r.name)
        else:
            failed.append(r.name)

    has_amd = len(ossature_project.components) > 0

    model_str = ""
    if ossature_project.llm:
        model_str = ossature_project.llm.model or ""

    return OssatureCapabilitiesSummary(
        project_name=report.ossature_project_name,
        project_language=report.ossature_language,
        ossature_model=model_str,
        budget_tier=report.budget_tier,
        budget_estimate_tokens=report.budget_estimate_tokens,
        budget_estimate_cost_usd=report.budget_estimate_cost_usd,
        spec_count=report.spec_count,
        spec_ids=report.spec_ids,
        has_architecture_specs=has_amd,
        architecture_component_count=len(ossature_project.components),
        has_output_dir=report.output_dir_exists,
        quality_score=report.quality_score,
        quality_level=report.quality_level,
        quality_checks_passed=passed,
        quality_checks_failed=failed,
        unsupported_language=report.unsupported_language,
        unsupported_tools=report.unsupported_tools,
        boundary_violations=report.boundary_violations,
    )


def _compute_dimensions(
    arm: SpecRequirementsSummary, oss: OssatureCapabilitiesSummary
) -> list[ComparisonDimension]:
    dims: list[ComparisonDimension] = []

    # 1. Language compatibility
    lang_gap = "MEETS" if not oss.unsupported_language else "GAP"
    dims.append(ComparisonDimension(
        dimension="Language compatibility",
        armature_value=arm.project_language,
        ossature_value=oss.project_language,
        gap=lang_gap,
        notes="Ossature language unsupported by armature toolchain" if lang_gap == "GAP" else "",
    ))

    # 2. Budget tier
    tier_gap = "MEETS" if arm.budget_tier == oss.budget_tier else "GAP"
    dims.append(ComparisonDimension(
        dimension="Budget tier",
        armature_value=f"{arm.budget_tier} ({arm.budget_max_tokens:,} tokens, ${arm.budget_max_cost_usd})",
        ossature_value=f"{oss.budget_tier} ({oss.budget_estimate_tokens:,} tokens, ${oss.budget_estimate_cost_usd})",
        gap=tier_gap,
    ))

    # 3. Budget max tokens
    token_gap = "MEETS" if oss.budget_estimate_tokens <= arm.budget_max_tokens else "GAP"
    dims.append(ComparisonDimension(
        dimension="Budget max tokens",
        armature_value=f"{arm.budget_max_tokens:,}",
        ossature_value=f"{oss.budget_estimate_tokens:,}",
        gap=token_gap,
    ))

    # 4. Unit test coverage minimum
    if not oss.has_output_dir:
        cov_gap = "UNKNOWN"
        cov_notes = "No output directory — cannot assess coverage"
    elif oss.quality_score * 100 >= arm.max_coverage_min:
        cov_gap = "MEETS"
        cov_notes = ""
    else:
        cov_gap = "GAP"
        cov_notes = f"Quality score {oss.quality_score:.0%} below {arm.max_coverage_min}% min"
    dims.append(ComparisonDimension(
        dimension="Unit test coverage minimum",
        armature_value=f"{arm.max_coverage_min}%",
        ossature_value=f"{oss.quality_score:.0%}" if oss.has_output_dir else "N/A",
        gap=cov_gap,
        notes=cov_notes,
    ))

    # 5. Integration tests required
    int_gap = "N/A" if arm.integration_test_required_count == 0 else "UNKNOWN"
    dims.append(ComparisonDimension(
        dimension="Integration tests required",
        armature_value=f"{arm.integration_test_required_count} specs require",
        ossature_value="Not tracked by ossature",
        gap=int_gap,
        notes="Ossature has no integration test concept",
    ))

    # 6. E2E tests required
    e2e_gap = "N/A" if arm.e2e_test_required_count == 0 else "UNKNOWN"
    dims.append(ComparisonDimension(
        dimension="E2E tests required",
        armature_value=f"{arm.e2e_test_required_count} specs require",
        ossature_value="Not tracked by ossature",
        gap=e2e_gap,
        notes="Ossature has no e2e test concept",
    ))

    # 7. Linting enforced
    if not arm.linting_enforced:
        lint_gap = "N/A"
    elif not oss.has_output_dir:
        lint_gap = "UNKNOWN"
    elif "lint" in oss.quality_checks_passed:
        lint_gap = "MEETS"
    else:
        lint_gap = "GAP"
    dims.append(ComparisonDimension(
        dimension="Linting enforced",
        armature_value="Yes" if arm.linting_enforced else "No",
        ossature_value=(
            "Pass" if "lint" in oss.quality_checks_passed
            else ("Fail" if "lint" in oss.quality_checks_failed else "Unknown")
        ),
        gap=lint_gap,
    ))

    # 8. Type checking enforced
    if not arm.type_check_enforced:
        tc_gap = "N/A"
    elif not oss.has_output_dir:
        tc_gap = "UNKNOWN"
    elif "type_check" in oss.quality_checks_passed:
        tc_gap = "MEETS"
    else:
        tc_gap = "GAP"
    dims.append(ComparisonDimension(
        dimension="Type checking enforced",
        armature_value="Yes" if arm.type_check_enforced else "No",
        ossature_value=(
            "Pass" if "type_check" in oss.quality_checks_passed
            else ("Fail" if "type_check" in oss.quality_checks_failed else "Unknown")
        ),
        gap=tc_gap,
    ))

    # 9. Acceptance criteria count
    dims.append(ComparisonDimension(
        dimension="Acceptance criteria count",
        armature_value=f"{arm.total_ac_count} ({arm.testable_ac_count} testable)",
        ossature_value=f"{oss.spec_count} specs (ACs in free text)",
        gap="N/A",
        notes="Ossature uses unstructured AC in markdown; not directly comparable",
    ))

    # 10. Human gate count
    dims.append(ComparisonDimension(
        dimension="Human gate count",
        armature_value=str(arm.human_gate_count),
        ossature_value="0 (no gate concept)",
        gap="GAP" if arm.human_gate_count > 0 else "N/A",
        notes="Armature enforces human review gates; ossature does not",
    ))

    # 11. Architecture defined
    arm_arch = f"{arm.architecture_layers} layers, {arm.architecture_boundaries} boundaries"
    oss_arch = f"{oss.architecture_component_count} components" if oss.has_architecture_specs else "None"
    arch_gap = "MEETS" if oss.has_architecture_specs and arm.architecture_layers > 0 else (
        "N/A" if arm.architecture_layers == 0 else "GAP"
    )
    dims.append(ComparisonDimension(
        dimension="Architecture defined",
        armature_value=arm_arch,
        ossature_value=oss_arch,
        gap=arch_gap,
    ))

    # 12. Quality gate threshold
    dims.append(ComparisonDimension(
        dimension="Quality gate threshold",
        armature_value=f"{arm.quality_gate_merge_ready:.0%} (merge-ready)",
        ossature_value=oss.quality_level if oss.has_output_dir else "N/A",
        gap="MEETS" if oss.quality_level == "merge_ready" else (
            "UNKNOWN" if not oss.has_output_dir else "GAP"
        ),
    ))

    # 13. Spec traceability
    dims.append(ComparisonDimension(
        dimension="Spec traceability",
        armature_value="Enabled (AC-to-test pattern)",
        ossature_value="Not supported",
        gap="GAP",
        notes="Armature traces ACs to test docstrings; ossature has no equivalent",
    ))

    return dims


def compare_projects(
    armature_root: Path,
    ossature_root: Path,
    *,
    pairing_rationale: str = "",
) -> SpecComparisonReport:
    """Compare an armature example project against an ossature fixture project."""
    config, specs = load_project_specs(armature_root)
    arm_summary = build_armature_summary(config, specs)

    oss_report = compare_ossature_project(ossature_root)
    oss_project = load_ossature_project(ossature_root)
    oss_summary = build_ossature_summary(oss_report, oss_project)

    dimensions = _compute_dimensions(arm_summary, oss_summary)
    gap_count = sum(1 for d in dimensions if d.gap == "GAP")
    meets_count = sum(1 for d in dimensions if d.gap == "MEETS")

    return SpecComparisonReport(
        armature_project=arm_summary.project_name,
        ossature_project=oss_summary.project_name,
        pairing_rationale=pairing_rationale,
        armature=arm_summary,
        ossature=oss_summary,
        dimensions=dimensions,
        overall_gap_count=gap_count,
        overall_meets_count=meets_count,
        generated_at=datetime.now(UTC).isoformat(),
    )


_PAIRINGS = [
    ("python-fastapi", "spenny", "Both Python; spenny has output files + architecture .amd"),
    ("typescript-nextjs", "math_quest", "Both alternative language stacks (TS vs Lua)"),
    ("monorepo", "markman", "Both multi-service/complex; markman is Rust CLI"),
]


def compare_all_projects(
    examples_dir: Path, fixtures_dir: Path
) -> list[SpecComparisonReport]:
    """Compare all three hard-coded pairings."""
    reports = []
    for arm_name, oss_name, rationale in _PAIRINGS:
        arm_root = examples_dir / arm_name
        oss_root = fixtures_dir / oss_name
        if arm_root.exists() and oss_root.exists():
            reports.append(compare_projects(arm_root, oss_root, pairing_rationale=rationale))
    return reports


def format_spec_comparison_report(report: SpecComparisonReport) -> str:
    """Format a comparison report as a text table."""
    lines = []
    lines.append(f"{'=' * 72}")
    lines.append(f"  Armature: {report.armature_project}  vs  Ossature: {report.ossature_project}")
    lines.append(f"  Rationale: {report.pairing_rationale}")
    lines.append(f"{'=' * 72}")
    lines.append("")

    hdr = f"{'Dimension':<30} {'Armature':<20} {'Ossature':<20} {'Gap':<8}"
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for d in report.dimensions:
        arm_val = d.armature_value[:18] if len(d.armature_value) > 18 else d.armature_value
        oss_val = d.ossature_value[:18] if len(d.ossature_value) > 18 else d.ossature_value
        dim_name = d.dimension[:28] if len(d.dimension) > 28 else d.dimension
        lines.append(f"{dim_name:<30} {arm_val:<20} {oss_val:<20} {d.gap:<8}")

    lines.append("")
    lines.append(f"  Summary: {report.overall_meets_count} MEETS, {report.overall_gap_count} GAPS")
    lines.append(f"  Generated: {report.generated_at}")
    lines.append("")
    return "\n".join(lines)


def format_all_comparisons(reports: list[SpecComparisonReport]) -> str:
    """Format all comparison reports with a summary table."""
    sections = [format_spec_comparison_report(r) for r in reports]

    summary_lines = []
    summary_lines.append(f"\n{'=' * 72}")
    summary_lines.append("  OVERALL SUMMARY")
    summary_lines.append(f"{'=' * 72}")
    summary_lines.append(f"{'Pairing':<45} {'MEETS':<8} {'GAPS':<8}")
    summary_lines.append("-" * 61)
    for r in reports:
        label = f"{r.armature_project} vs {r.ossature_project}"
        summary_lines.append(f"{label:<45} {r.overall_meets_count:<8} {r.overall_gap_count:<8}")
    summary_lines.append("")

    return "\n".join(sections) + "\n".join(summary_lines)


def spec_comparison_report_to_dict(report: SpecComparisonReport) -> dict:
    """Convert report to JSON-serializable dict."""
    return asdict(report)
