"""Tests for architecture/boundary.py -- layer boundary enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature._internal.types import Violation
from armature.architecture.boundary import (
    check_boundaries,
    run_boundary_check,
    _resolve_layer,
    _import_to_layer,
    _is_shared_import,
)
from armature.config.schema import ArchitectureConfig, BoundaryRule, LayerDef


@pytest.fixture
def arch_config() -> ArchitectureConfig:
    return ArchitectureConfig(
        enabled=True,
        layers=[
            LayerDef(name="models", dirs=["src/models/"]),
            LayerDef(name="services", dirs=["src/services/"]),
            LayerDef(name="routes", dirs=["src/routes/"]),
        ],
        boundaries=[
            BoundaryRule(**{"from": "models", "to": ["routes"]}),
            BoundaryRule(**{"from": "services", "to": ["routes"]}),
        ],
        allowed_shared=["src/utils/", "src/config/"],
    )


class TestResolveLayer:
    """Tests for _resolve_layer()."""

    def test_resolves_models(self, arch_config: ArchitectureConfig, tmp_path: Path):
        f = tmp_path / "src" / "models" / "user.py"
        f.parent.mkdir(parents=True)
        layer = _resolve_layer(f, arch_config, tmp_path)
        assert layer == "models"

    def test_resolves_none_for_unknown(self, arch_config: ArchitectureConfig, tmp_path: Path):
        f = tmp_path / "scripts" / "deploy.py"
        f.parent.mkdir(parents=True)
        layer = _resolve_layer(f, arch_config, tmp_path)
        assert layer is None


class TestImportToLayer:
    """Tests for _import_to_layer()."""

    def test_maps_module_to_layer(self, arch_config: ArchitectureConfig):
        layer = _import_to_layer("src.routes.api", arch_config)
        assert layer == "routes"

    def test_returns_none_for_unmapped(self, arch_config: ArchitectureConfig):
        layer = _import_to_layer("os.path", arch_config)
        assert layer is None


class TestIsSharedImport:
    """Tests for _is_shared_import()."""

    def test_shared_import(self, arch_config: ArchitectureConfig):
        assert _is_shared_import("src.utils.helpers", arch_config) is True

    def test_non_shared_import(self, arch_config: ArchitectureConfig):
        assert _is_shared_import("src.routes.api", arch_config) is False


class TestCheckBoundaries:
    """Tests for check_boundaries()."""

    def test_detects_violation(self, tmp_path: Path, arch_config: ArchitectureConfig):
        # models importing from routes = violation
        models_dir = tmp_path / "src" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "user.py").write_text(
            "from src.routes.api import login\n", encoding="utf-8"
        )

        violations = check_boundaries(arch_config, tmp_path)
        assert len(violations) >= 1
        assert any("LAYER BOUNDARY CROSSED" in v.message for v in violations)

    def test_no_violation_for_allowed_direction(self, tmp_path: Path, arch_config: ArchitectureConfig):
        # routes importing from services = allowed (not in forbidden map)
        routes_dir = tmp_path / "src" / "routes"
        routes_dir.mkdir(parents=True)
        (routes_dir / "api.py").write_text(
            "from src.services.auth import authenticate\n", encoding="utf-8"
        )

        violations = check_boundaries(arch_config, tmp_path)
        assert len(violations) == 0

    def test_shared_imports_always_allowed(self, tmp_path: Path, arch_config: ArchitectureConfig):
        models_dir = tmp_path / "src" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "user.py").write_text(
            "from src.utils.helpers import format_name\n", encoding="utf-8"
        )

        violations = check_boundaries(arch_config, tmp_path)
        assert len(violations) == 0


class TestRunBoundaryCheck:
    """Tests for run_boundary_check() CheckResult."""

    def test_pass_returns_clean(self, tmp_path: Path, arch_config: ArchitectureConfig):
        # Empty dirs = no violations
        result = run_boundary_check(arch_config, tmp_path)
        assert result.passed is True
        assert result.violation_count == 0
        assert result.score == 1.0
