"""Tests for the Armature plugin system."""

from __future__ import annotations

import pytest

from armature._internal.types import CheckResult, GCFinding, HealResult, Severity
from armature.plugins import ArmaturePlugin, PluginRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _PassPlugin(ArmaturePlugin):
    name = "pass-plugin"
    version = "1.0.0"
    description = "Always passes"

    def on_check(self, file_path, results):
        return [*results, CheckResult(name="pass_check", passed=True, score=1.0, weight=10)]


class _FailPlugin(ArmaturePlugin):
    name = "fail-plugin"
    version = "1.0.0"
    description = "Adds a failing check"

    def on_check(self, file_path, results):
        return [*results, CheckResult(name="fail_check", passed=False, violation_count=3, score=0.7, weight=10)]


class _BrokenPlugin(ArmaturePlugin):
    name = "broken-plugin"

    def on_check(self, file_path, results):
        raise RuntimeError("intentional error")

    def on_heal(self, failures, results):
        raise RuntimeError("intentional error")

    def on_gc(self, findings):
        raise RuntimeError("intentional error")


class _NamelessPlugin(ArmaturePlugin):
    pass  # name = "" -- should fail on register


@pytest.fixture()
def registry() -> PluginRegistry:
    return PluginRegistry()


@pytest.fixture()
def populated_registry(registry: PluginRegistry) -> PluginRegistry:
    registry.register(_PassPlugin())
    registry.register(_FailPlugin())
    return registry


# ---------------------------------------------------------------------------
# ArmaturePlugin base class
# ---------------------------------------------------------------------------

class TestArmaturePlugin:
    def test_default_on_check_is_passthrough(self):
        plugin = ArmaturePlugin()
        results = [CheckResult(name="lint", passed=True)]
        assert plugin.on_check(None, results) is results

    def test_default_on_heal_is_passthrough(self):
        plugin = ArmaturePlugin()
        results = [HealResult(failure_type="lint", attempt=1, fixed=True, remaining_errors=0)]
        assert plugin.on_heal({"lint"}, results) is results

    def test_default_on_gc_is_passthrough(self):
        plugin = ArmaturePlugin()
        findings = [GCFinding(agent="docs", category="stale", file="README.md", message="stale")]
        assert plugin.on_gc(findings) is findings

    def test_default_attributes(self):
        plugin = ArmaturePlugin()
        assert plugin.name == ""
        assert plugin.version == "0.0.0"
        assert plugin.description == ""


# ---------------------------------------------------------------------------
# PluginRegistry -- registration
# ---------------------------------------------------------------------------

class TestPluginRegistryRegistration:
    def test_register_plugin(self, registry: PluginRegistry):
        registry.register(_PassPlugin())
        assert len(registry) == 1

    def test_register_replaces_same_name(self, registry: PluginRegistry):
        registry.register(_PassPlugin())
        registry.register(_PassPlugin())  # same name, second registration
        assert len(registry) == 1

    def test_register_nameless_raises(self, registry: PluginRegistry):
        with pytest.raises(ValueError, match="non-empty name"):
            registry.register(_NamelessPlugin())

    def test_get_returns_plugin(self, registry: PluginRegistry):
        plugin = _PassPlugin()
        registry.register(plugin)
        assert registry.get("pass-plugin") is plugin

    def test_get_returns_none_for_missing(self, registry: PluginRegistry):
        assert registry.get("nonexistent") is None

    def test_list_plugins(self, populated_registry: PluginRegistry):
        names = [p.name for p in populated_registry.list_plugins()]
        assert "pass-plugin" in names
        assert "fail-plugin" in names


# ---------------------------------------------------------------------------
# PluginRegistry -- lifecycle dispatch
# ---------------------------------------------------------------------------

class TestPluginRegistryDispatch:
    def test_run_on_check_accumulates_results(self, populated_registry: PluginRegistry):
        base = [CheckResult(name="lint", passed=True)]
        out = populated_registry.run_on_check(None, base)
        names = {r.name for r in out}
        assert "lint" in names
        assert "pass_check" in names
        assert "fail_check" in names

    def test_run_on_check_with_file_path(self, populated_registry: PluginRegistry):
        base: list[CheckResult] = []
        out = populated_registry.run_on_check("src/foo.py", base)
        assert any(r.name == "pass_check" for r in out)

    def test_run_on_heal_is_passthrough_by_default(self, registry: PluginRegistry):
        registry.register(_PassPlugin())
        results = [HealResult(failure_type="lint", attempt=1, fixed=True, remaining_errors=0)]
        out = registry.run_on_heal({"lint"}, results)
        assert out == results

    def test_run_on_gc_is_passthrough_by_default(self, registry: PluginRegistry):
        registry.register(_PassPlugin())
        findings = [GCFinding(agent="docs", category="stale", file="x.md", message="old")]
        out = registry.run_on_gc(findings)
        assert out == findings

    def test_broken_plugin_does_not_crash_registry(self, registry: PluginRegistry):
        """A plugin that raises must not prevent other plugins from running."""
        registry.register(_BrokenPlugin())
        registry.register(_PassPlugin())

        results = registry.run_on_check(None, [])
        assert any(r.name == "pass_check" for r in results)

        heal_results: list[HealResult] = []
        out = registry.run_on_heal({"lint"}, heal_results)
        assert out == heal_results

        gc_findings: list[GCFinding] = []
        out_gc = registry.run_on_gc(gc_findings)
        assert out_gc == gc_findings

    def test_empty_registry_returns_inputs_unchanged(self, registry: PluginRegistry):
        results = [CheckResult(name="lint", passed=True)]
        assert registry.run_on_check(None, results) == results

        findings = [GCFinding(agent="docs", category="stale", file="x.md", message="old",
                              severity=Severity.WARNING)]
        assert registry.run_on_gc(findings) == findings


# ---------------------------------------------------------------------------
# PluginRegistry -- entry-point loading
# ---------------------------------------------------------------------------

class TestPluginRegistryEntryPoints:
    def test_load_entry_points_does_not_crash_with_no_eps(self, registry: PluginRegistry):
        """Calling load_entry_points when no plugins are installed must not raise."""
        registry.load_entry_points()  # should be a no-op in the test environment

    def test_load_entry_points_ignores_bad_ep(self, registry: PluginRegistry, monkeypatch):
        """A broken entry point must be skipped, not propagated."""
        class _BadEP:
            name = "bad"
            def load(self):
                raise ImportError("missing dependency")

        monkeypatch.setattr(
            "armature.plugins.entry_points",
            lambda group: [_BadEP()] if group == "armature.plugins" else [],
        )
        registry.load_entry_points()
        assert len(registry) == 0
