"""Spec YAML loader — reads armature spec files into structured dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from armature.config.loader import load_config
from armature.config.schema import ArmatureConfig


@dataclass
class EvalRequirements:
    unit_test_coverage_min: int = 0
    integration_test_required: bool = False
    e2e_test_required: bool = False
    linting_must_pass: bool = False
    type_check_must_pass: bool = False


@dataclass
class AcceptanceCriterion:
    id: str
    description: str
    testable: bool = True


@dataclass
class SpecRecord:
    spec_id: str
    title: str
    spec_type: str
    priority: str
    acceptance_criteria: list[AcceptanceCriterion]
    eval_requirements: EvalRequirements
    human_gates: list[dict] = field(default_factory=list)
    scope_modules: list[str] = field(default_factory=list)
    touches_api: bool = False
    touches_ui: bool = False
    new_files_expected: list[str] = field(default_factory=list)
    modified_files_expected: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    source_file: Path = field(default_factory=lambda: Path("."))


def load_spec(path: Path) -> SpecRecord:
    """Load a single spec YAML file into a SpecRecord."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}

    eval_raw = raw.get("eval", {}) or {}
    eval_req = EvalRequirements(
        unit_test_coverage_min=eval_raw.get("unit_test_coverage_min", 0),
        integration_test_required=eval_raw.get("integration_test_required", False),
        e2e_test_required=eval_raw.get("e2e_test_required", False),
        linting_must_pass=eval_raw.get("linting_must_pass", False),
        type_check_must_pass=eval_raw.get("type_check_must_pass", False),
    )

    ac_list = []
    for ac in raw.get("acceptance_criteria", []) or []:
        ac_list.append(AcceptanceCriterion(
            id=ac.get("id", ""),
            description=ac.get("description", ""),
            testable=ac.get("testable", True),
        ))

    scope = raw.get("scope", {}) or {}

    return SpecRecord(
        spec_id=raw.get("spec_id", ""),
        title=raw.get("title", ""),
        spec_type=raw.get("type", ""),
        priority=raw.get("priority", "medium"),
        acceptance_criteria=ac_list,
        eval_requirements=eval_req,
        human_gates=raw.get("human_gates", []) or [],
        scope_modules=scope.get("modules", []) or [],
        touches_api=scope.get("touches_api", False),
        touches_ui=scope.get("touches_ui", False),
        new_files_expected=scope.get("new_files_expected", []) or [],
        modified_files_expected=scope.get("modified_files_expected", []) or [],
        depends_on=raw.get("depends_on", []) or [],
        blocks=raw.get("blocks", []) or [],
        source_file=path,
    )


def load_all_specs(specs_dir: Path) -> list[SpecRecord]:
    """Load all spec YAML files from a directory, skipping templates/."""
    specs = []
    for path in sorted(specs_dir.glob("*.yaml")):
        if "templates" in path.parts:
            continue
        specs.append(load_spec(path))
    for path in sorted(specs_dir.glob("*.yml")):
        if "templates" in path.parts:
            continue
        specs.append(load_spec(path))
    return sorted(specs, key=lambda s: s.spec_id)


def load_project_specs(project_root: Path) -> tuple[ArmatureConfig, list[SpecRecord]]:
    """Load armature.yaml config and all specs from a project."""
    config_path = project_root / "armature.yaml"
    if not config_path.exists():
        config_path = project_root / "armature.yml"

    config = load_config(config_path if config_path.exists() else None)

    specs_dir = project_root / config.specs.dir
    if not specs_dir.exists():
        return config, []

    return config, load_all_specs(specs_dir)
