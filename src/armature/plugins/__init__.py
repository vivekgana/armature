"""Armature plugin system -- extensible lifecycle hooks for third-party quality checks.

Plugin authors create a class that subclasses :class:`ArmaturePlugin`, package it as a
Python distribution, and declare it under the ``armature.plugins`` entry-point group::

    # pyproject.toml
    [project.entry-points."armature.plugins"]
    my-plugin = "my_package:MyPlugin"

Armature discovers and loads all registered plugins at runtime.

Built-in plugins (TypeScript quality) are registered the same way — they prove the
interface and serve as reference implementations for community authors.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from armature._internal.types import CheckResult, GCFinding, HealResult

logger = logging.getLogger(__name__)


class ArmaturePlugin:
    """Base class for Armature plugins.

    Subclass this and override the lifecycle hooks you need.  All hooks receive
    the current list of results and *must* return the (possibly modified) list —
    this allows plugins to add, filter, or annotate results.

    Attributes:
        name: Unique plugin identifier (e.g. ``"typescript-quality"``).
        version: Plugin version string.
        description: Short human-readable description shown in ``armature plugin list``.
    """

    name: str = ""
    version: str = "0.0.0"
    description: str = ""

    def on_check(
        self,
        file_path: str | None,
        results: list[CheckResult],
    ) -> list[CheckResult]:
        """Called after the built-in quality checks finish.

        Args:
            file_path: The file being checked, or ``None`` for a project-wide run.
            results: Current list of :class:`~armature._internal.types.CheckResult`.

        Returns:
            Updated results list (add, remove, or annotate items as needed).
        """
        return results

    def on_heal(
        self,
        failures: set[str],
        results: list[HealResult],
    ) -> list[HealResult]:
        """Called during the self-healing pipeline.

        Args:
            failures: Set of failure type names requested for healing.
            results: Current list of :class:`~armature._internal.types.HealResult`.

        Returns:
            Updated heal results list.
        """
        return results

    def on_gc(
        self,
        findings: list[GCFinding],
    ) -> list[GCFinding]:
        """Called after the garbage collection sweep.

        Args:
            findings: Current list of :class:`~armature._internal.types.GCFinding`.

        Returns:
            Updated findings list.
        """
        return findings


class PluginRegistry:
    """Registry that holds and dispatches to all loaded :class:`ArmaturePlugin` instances.

    Use the module-level :data:`registry` singleton rather than constructing a new
    instance in application code.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ArmaturePlugin] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, plugin: ArmaturePlugin) -> None:
        """Register a plugin instance.

        Args:
            plugin: An :class:`ArmaturePlugin` instance with a non-empty ``name``.

        Raises:
            ValueError: If the plugin name is empty.
        """
        if not plugin.name:
            raise ValueError("Plugin must have a non-empty name")
        if plugin.name in self._plugins:
            logger.debug("Replacing existing plugin %r", plugin.name)
        self._plugins[plugin.name] = plugin

    def load_entry_points(self) -> None:
        """Discover and load all plugins registered under ``armature.plugins``.

        Silently skips plugins that fail to load so that a broken plugin does not
        prevent Armature from running.
        """
        eps = entry_points(group="armature.plugins")
        for ep in eps:
            try:
                plugin_cls = ep.load()
                plugin = plugin_cls()
                self.register(plugin)
                logger.debug("Loaded plugin %r from entry point %r", plugin.name, ep.name)
            except Exception as exc:
                logger.warning("Failed to load plugin from entry point %r: %s", ep.name, exc)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_plugins(self) -> list[ArmaturePlugin]:
        """Return all registered plugins in registration order."""
        return list(self._plugins.values())

    def get(self, name: str) -> ArmaturePlugin | None:
        """Return the plugin with the given name, or ``None``."""
        return self._plugins.get(name)

    def __len__(self) -> int:
        return len(self._plugins)

    # ------------------------------------------------------------------
    # Lifecycle dispatch
    # ------------------------------------------------------------------

    def run_on_check(
        self,
        file_path: str | None,
        results: list[CheckResult],
    ) -> list[CheckResult]:
        """Invoke :meth:`ArmaturePlugin.on_check` for every registered plugin."""
        for plugin in self._plugins.values():
            try:
                results = plugin.on_check(file_path, results)
            except Exception as exc:
                logger.warning("Plugin %r raised in on_check: %s", plugin.name, exc)
        return results

    def run_on_heal(
        self,
        failures: set[str],
        results: list[HealResult],
    ) -> list[HealResult]:
        """Invoke :meth:`ArmaturePlugin.on_heal` for every registered plugin."""
        for plugin in self._plugins.values():
            try:
                results = plugin.on_heal(failures, results)
            except Exception as exc:
                logger.warning("Plugin %r raised in on_heal: %s", plugin.name, exc)
        return results

    def run_on_gc(
        self,
        findings: list[GCFinding],
    ) -> list[GCFinding]:
        """Invoke :meth:`ArmaturePlugin.on_gc` for every registered plugin."""
        for plugin in self._plugins.values():
            try:
                findings = plugin.on_gc(findings)
            except Exception as exc:
                logger.warning("Plugin %r raised in on_gc: %s", plugin.name, exc)
        return findings


#: Module-level singleton registry. Import this in application code.
registry: PluginRegistry = PluginRegistry()

__all__ = [
    "ArmaturePlugin",
    "PluginRegistry",
    "registry",
]
