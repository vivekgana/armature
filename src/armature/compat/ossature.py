"""Convert ossature projects to armature configuration.

Maps ossature.toml + .smd/.amd specs to an ArmatureConfig that can
drive budget-controlled quality checks on ossature-generated output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from armature.compat._ossature_model import (
    OssatureComponent,
    OssatureProjectFull,
    load_ossature_project,
)
from armature.config.schema import (
    ArmatureConfig,
    ArchitectureConfig,
    BoundaryRule,
    BudgetConfig,
    BudgetTier,
    ClaudeCodeConfig,
    IntegrationsConfig,
    LayerDef,
    PostWriteConfig,
    ProjectConfig,
    QualityConfig,
    SpecConfig,
    ToolCheckConfig,
    TraceabilityConfig,
)


_LANGUAGE_MAP: dict[str, str] = {
    "python": "python",
    "rust": "rust",
    "typescript": "typescript",
    "javascript": "javascript",
    "go": "go",
    "java": "java",
    "kotlin": "kotlin",
    "ruby": "ruby",
}

_TEST_RUNNER_MAP: dict[str, str] = {
    "pytest": "pytest",
    "python -m pytest": "pytest",
    "jest": "jest",
    "vitest": "vitest",
    "unittest": "unittest",
}

_LINT_TOOL_MAP: dict[str, str] = {
    "ruff": "ruff",
    "flake8": "flake8",
    "pylint": "pylint",
    "eslint": "eslint",
    "biome": "biome",
}

_MODEL_TIER_MAP: dict[str, str] = {
    "opus": "high",
    "sonnet": "medium",
    "haiku": "low",
    "gpt-4o": "medium",
    "gpt-4o-mini": "low",
    "gpt-4": "high",
    "gemini-pro": "medium",
    "gemini-flash": "low",
    "devstral": "medium",
}


@dataclass
class ConversionWarning:
    field: str
    ossature_value: str
    reason: str
    fallback: str


@dataclass
class ConversionResult:
    config: ArmatureConfig
    warnings: list[ConversionWarning] = field(default_factory=list)
    ossature_project: OssatureProjectFull | None = None


def _infer_model_tier(model_str: str) -> str:
    """Infer budget tier from an ossature model string like 'anthropic:claude-sonnet-4-5'."""
    normalized = model_str.lower().split(":")[-1] if ":" in model_str else model_str.lower()
    for key, tier in _MODEL_TIER_MAP.items():
        if key in normalized:
            return tier
    return "medium"


def _map_language(raw: str, warnings: list[ConversionWarning]) -> str:
    """Map ossature language to armature ALLOWED_LANGUAGES, with fallback."""
    mapped = _LANGUAGE_MAP.get(raw.lower())
    if mapped:
        return mapped
    warnings.append(ConversionWarning(
        field="project.language",
        ossature_value=raw,
        reason=f"Language '{raw}' is not supported by armature; quality checks will use Python toolchain defaults",
        fallback="python",
    ))
    return "python"


def _map_test_runner(runner: str, warnings: list[ConversionWarning]) -> str:
    """Map ossature test runner to armature ALLOWED_TOOLS."""
    mapped = _TEST_RUNNER_MAP.get(runner.lower())
    if mapped:
        return mapped
    if runner:
        warnings.append(ConversionWarning(
            field="quality.checks.test.tool",
            ossature_value=runner,
            reason=f"Test runner '{runner}' is not in armature's allowed tools",
            fallback="",
        ))
    return ""


def _build_architecture(
    components: list[OssatureComponent],
) -> ArchitectureConfig:
    """Build armature ArchitectureConfig from ossature .amd components."""
    if not components:
        return ArchitectureConfig(enabled=False)

    layers: list[LayerDef] = []
    seen_paths: set[str] = set()

    for comp in components:
        if not comp.path or comp.path in seen_paths:
            continue
        seen_paths.add(comp.path)
        dir_path = str(Path(comp.path).parent) + "/"
        layers.append(LayerDef(name=comp.name.lower().replace(" ", "_"), dirs=[dir_path]))

    boundaries: list[BoundaryRule] = []
    name_to_layer = {comp.name.lower().replace(" ", "_"): comp for comp in components if comp.path}

    for comp in components:
        comp_name = comp.name.lower().replace(" ", "_")
        for dep_name_raw in comp.depends:
            dep_name = dep_name_raw.lower().replace(" ", "_")
            if dep_name in name_to_layer and comp_name in name_to_layer:
                boundaries.append(BoundaryRule(**{"from": dep_name, "to": [comp_name]}))

    return ArchitectureConfig(
        enabled=True,
        layers=layers,
        boundaries=boundaries,
    )


def _build_quality(
    ossature: OssatureProjectFull,
    language: str,
    warnings: list[ConversionWarning],
) -> QualityConfig:
    """Build armature QualityConfig from ossature build/test config."""
    checks: dict[str, ToolCheckConfig] = {}

    if language == "python":
        checks["lint"] = ToolCheckConfig(tool="ruff", args=["check", "--statistics"], weight=25)
        checks["type_check"] = ToolCheckConfig(tool="mypy", args=["--no-error-summary"], weight=25)
    elif language == "typescript":
        checks["lint"] = ToolCheckConfig(tool="eslint", args=[], weight=25)
        checks["type_check"] = ToolCheckConfig(tool="tsc", args=["--noEmit"], weight=25)
    elif language == "rust":
        checks["lint"] = ToolCheckConfig(tool="", args=[], weight=25)
        checks["type_check"] = ToolCheckConfig(tool="", args=[], weight=25)
        warnings.append(ConversionWarning(
            field="quality.checks",
            ossature_value=f"rust (verify: {ossature.build.verify})",
            reason="Rust lint/type tools (clippy, cargo check) not in armature's allowed tools",
            fallback="empty tool (graceful skip)",
        ))

    test_tool = _map_test_runner(ossature.test.runner, warnings)
    coverage_min = int(ossature.test.coverage_threshold) if ossature.test.coverage_threshold else None
    checks["test"] = ToolCheckConfig(
        tool=test_tool,
        args=["-x", "--tb=short"] if test_tool == "pytest" else [],
        weight=20,
        coverage_min=coverage_min,
    )

    return QualityConfig(
        enabled=True,
        checks=checks,
        post_write=PostWriteConfig(enabled=True, tools=["lint", "type_check"]),
    )


def _build_budget(ossature: OssatureProjectFull) -> BudgetConfig:
    """Build armature BudgetConfig from ossature LLM model config."""
    tier = _infer_model_tier(ossature.llm.model)

    tier_to_tokens = {"low": 100_000, "medium": 500_000, "high": 1_000_000}
    tier_to_cost = {"low": 2.0, "medium": 10.0, "high": 20.0}

    return BudgetConfig(
        enabled=True,
        defaults={
            "low": BudgetTier(max_tokens=100_000, max_cost_usd=2.0),
            "medium": BudgetTier(max_tokens=500_000, max_cost_usd=10.0),
            "high": BudgetTier(max_tokens=1_000_000, max_cost_usd=20.0),
            "critical": BudgetTier(max_tokens=2_000_000, max_cost_usd=40.0),
        },
    )


def convert_ossature_project(root: Path) -> ConversionResult:
    """Convert an ossature project at root to an ArmatureConfig."""
    ossature = load_ossature_project(root)
    warnings: list[ConversionWarning] = []

    language = _map_language(ossature.output.language, warnings)

    project = ProjectConfig(
        name=ossature.project.name,
        language=language,
        src_dir=ossature.output.dir + "/",
        test_dir="tests/",
    )

    quality = _build_quality(ossature, language, warnings)
    architecture = _build_architecture(ossature.components)
    budget = _build_budget(ossature)

    spec_config = SpecConfig(enabled=False)
    if ossature.specs:
        spec_config = SpecConfig(
            enabled=True,
            dir=ossature.project.spec_dir + "/",
            id_pattern=r"^[A-Za-z0-9_\-]{1,64}$",
            traceability=TraceabilityConfig(enabled=False),
        )

    integrations = IntegrationsConfig(
        claude_code=ClaudeCodeConfig(enabled=True, post_tool_use=True, pre_session=True),
    )

    config = ArmatureConfig(
        project=project,
        budget=budget,
        quality=quality,
        architecture=architecture,
        specs=spec_config,
        integrations=integrations,
    )

    return ConversionResult(
        config=config,
        warnings=warnings,
        ossature_project=ossature,
    )


def conversion_result_to_yaml(result: ConversionResult) -> str:
    """Serialize a ConversionResult to armature.yaml YAML string."""
    config_dict = result.config.model_dump(exclude_defaults=False)

    _clean_for_yaml(config_dict)

    lines = ["# Armature config -- converted from ossature project"]
    if result.ossature_project:
        lines.append(f"# Source: {result.ossature_project.project.name} (ossature)")
    if result.warnings:
        lines.append("#")
        lines.append("# Conversion warnings:")
        for w in result.warnings:
            lines.append(f"#   - {w.field}: {w.reason} (fallback: {w.fallback})")
    lines.append("")

    yaml_str = yaml.dump(config_dict, default_flow_style=False, sort_keys=False, indent=2)
    return "\n".join(lines) + yaml_str


def _clean_for_yaml(d: dict) -> None:
    """Recursively convert Pydantic-style dict for cleaner YAML output."""
    for key, val in list(d.items()):
        if isinstance(val, dict):
            _clean_for_yaml(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _clean_for_yaml(item)
    if "from_layer" in d:
        d["from"] = d.pop("from_layer")
    if "to_layers" in d:
        d["to"] = d.pop("to_layers")
