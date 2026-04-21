"""Tests for ossature → armature conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.compat._ossature_model import (
    load_ossature_project,
    parse_amd_file,
    parse_smd_file,
)
from armature.compat.ossature import (
    _infer_model_tier,
    _map_language,
    conversion_result_to_yaml,
    convert_ossature_project,
)


class TestOssatureParser:
    def test_parse_ossature_toml_spenny(self, spenny_project: Path) -> None:
        proj = load_ossature_project(spenny_project)
        assert proj.project.name == "Spenny"
        assert proj.output.language == "python"
        assert proj.llm.model == "mistral:devstral-latest"

    def test_parse_ossature_toml_markman(self, markman_project: Path) -> None:
        proj = load_ossature_project(markman_project)
        assert proj.project.name == "markman"
        assert proj.output.language == "rust"
        assert proj.build.verify == "cargo check"
        assert proj.build.setup == "cargo init --name markman"

    def test_parse_ossature_toml_math_quest(self, math_quest_project: Path) -> None:
        proj = load_ossature_project(math_quest_project)
        assert proj.project.name == "math_quest"
        assert proj.output.language == "lua"

    def test_parse_smd_extracts_directives(self, spenny_project: Path) -> None:
        smd = spenny_project / "specs" / "expense_tracker.smd"
        spec = parse_smd_file(smd)
        assert spec.id == "EXPENSE_TRACKER"
        assert spec.status == "draft"
        assert spec.priority == "high"

    def test_parse_amd_extracts_components(self, spenny_project: Path) -> None:
        amd = spenny_project / "specs" / "expense_tracker.amd"
        components = parse_amd_file(amd)
        assert len(components) == 3
        paths = [c.path for c in components]
        assert "src/spenny/storage.py" in paths
        assert "src/spenny/core.py" in paths
        assert "src/spenny/cli.py" in paths

    def test_load_project_discovers_specs(self, spenny_project: Path) -> None:
        proj = load_ossature_project(spenny_project)
        assert len(proj.specs) == 1
        assert proj.specs[0].id == "EXPENSE_TRACKER"

    def test_load_project_discovers_components(self, spenny_project: Path) -> None:
        proj = load_ossature_project(spenny_project)
        assert len(proj.components) == 3

    def test_load_project_no_toml_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=r"No ossature\.toml"):
            load_ossature_project(tmp_path)

    def test_markman_has_specs_no_components(self, markman_project: Path) -> None:
        proj = load_ossature_project(markman_project)
        assert len(proj.specs) == 1
        assert proj.specs[0].id == "CLI_BOOKMARKS"
        assert len(proj.components) == 0


class TestLanguageMapping:
    def test_python_maps_correctly(self, spenny_project: Path) -> None:
        result = convert_ossature_project(spenny_project)
        assert result.config.project.language == "python"

    def test_rust_maps_correctly(self, markman_project: Path) -> None:
        result = convert_ossature_project(markman_project)
        assert result.config.project.language == "rust"

    def test_lua_produces_warning(self, math_quest_project: Path) -> None:
        result = convert_ossature_project(math_quest_project)
        assert result.config.project.language == "python"
        assert any(w.field == "project.language" for w in result.warnings)
        lua_warning = next(w for w in result.warnings if w.field == "project.language")
        assert "lua" in lua_warning.ossature_value.lower()

    def test_map_language_direct(self) -> None:
        warnings: list = []
        assert _map_language("python", warnings) == "python"
        assert _map_language("rust", warnings) == "rust"
        assert _map_language("typescript", warnings) == "typescript"
        assert not warnings

    def test_map_language_unsupported(self) -> None:
        warnings: list = []
        assert _map_language("zig", warnings) == "python"
        assert len(warnings) == 1


class TestArchitectureMapping:
    def test_amd_components_become_layers(self, spenny_project: Path) -> None:
        result = convert_ossature_project(spenny_project)
        assert result.config.architecture.enabled is True
        assert len(result.config.architecture.layers) == 3

    def test_no_amd_disables_architecture(self, markman_project: Path) -> None:
        result = convert_ossature_project(markman_project)
        assert result.config.architecture.enabled is False

    def test_boundaries_from_depends(self, spenny_project: Path) -> None:
        result = convert_ossature_project(spenny_project)
        assert len(result.config.architecture.boundaries) > 0


class TestBudgetInference:
    def test_opus_maps_to_high(self) -> None:
        assert _infer_model_tier("anthropic:claude-opus-4-6") == "high"

    def test_sonnet_maps_to_medium(self) -> None:
        assert _infer_model_tier("anthropic:claude-sonnet-4-6") == "medium"

    def test_haiku_maps_to_low(self) -> None:
        assert _infer_model_tier("anthropic:claude-haiku-4-5-20251001") == "low"

    def test_devstral_maps_to_medium(self) -> None:
        assert _infer_model_tier("mistral:devstral-latest") == "medium"

    def test_unknown_defaults_to_medium(self) -> None:
        assert _infer_model_tier("unknown:mystery-model") == "medium"

    def test_budget_enabled_after_conversion(self, spenny_project: Path) -> None:
        result = convert_ossature_project(spenny_project)
        assert result.config.budget.enabled is True


class TestSpecConfig:
    def test_specs_enabled_when_smd_exists(self, spenny_project: Path) -> None:
        result = convert_ossature_project(spenny_project)
        assert result.config.specs.enabled is True
        assert result.config.specs.id_pattern == r"^[A-Za-z0-9_\-]{1,64}$"

    def test_specs_disabled_when_no_smd(self, tmp_path: Path) -> None:
        (tmp_path / "ossature.toml").write_text(
            '[project]\nname = "empty"\n[output]\nlanguage = "python"\n[llm]\nmodel = "x"\n',
            encoding="utf-8",
        )
        result = convert_ossature_project(tmp_path)
        assert result.config.specs.enabled is False


class TestYamlSerialization:
    def test_conversion_produces_valid_yaml(self, spenny_project: Path) -> None:
        import yaml
        result = convert_ossature_project(spenny_project)
        yaml_str = conversion_result_to_yaml(result)
        parsed = yaml.safe_load(yaml_str)
        assert parsed["project"]["name"] == "Spenny"
        assert parsed["project"]["language"] == "python"

    def test_yaml_includes_warning_comments(self, math_quest_project: Path) -> None:
        result = convert_ossature_project(math_quest_project)
        yaml_str = conversion_result_to_yaml(result)
        assert "Conversion warnings" in yaml_str
        assert "lua" in yaml_str.lower()
