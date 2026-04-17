"""GC orchestrator -- runs garbage collection agents."""

from __future__ import annotations

from pathlib import Path

from armature._internal.types import GCFinding
from armature.config.schema import ArmatureConfig, GCConfig


class GCRunner:
    """Orchestrates garbage collection agents."""

    def __init__(self, gc_config: GCConfig, config: ArmatureConfig) -> None:
        self.gc_config = gc_config
        self.config = config
        self.root = Path.cwd()

    def run(self, *, agent_name: str | None = None) -> list[GCFinding]:
        """Run GC agents and collect findings."""
        findings: list[GCFinding] = []

        agents = {
            "architecture": self._gc_architecture,
            "docs": self._gc_docs,
            "dead_code": self._gc_dead_code,
            "budget": self._gc_budget,
        }

        for name, agent_fn in agents.items():
            if agent_name and name != agent_name:
                continue
            agent_config = self.gc_config.agents.get(name)
            if agent_config is None or not agent_config.enabled:
                continue
            findings.extend(agent_fn())

        return findings

    def _gc_architecture(self) -> list[GCFinding]:
        """Detect architecture drift."""
        findings: list[GCFinding] = []

        if self.config.architecture.enabled:
            from armature.architecture.boundary import check_boundaries
            from armature.architecture.conformance import check_conformance

            for v in check_boundaries(self.config.architecture, self.root):
                findings.append(GCFinding(
                    agent="architecture", category="boundary", file=v.file,
                    message=v.message,
                ))
            for v in check_conformance(self.config.architecture, self.root):
                findings.append(GCFinding(
                    agent="architecture", category="conformance", file=v.file,
                    message=v.message,
                ))

        return findings

    def _gc_docs(self) -> list[GCFinding]:
        """Detect stale documentation references."""
        from armature.gc.agents.docs import scan_docs
        agent_config = self.gc_config.agents.get("docs")
        watched = agent_config.watched_files if agent_config else []
        return scan_docs(self.root, watched)

    def _gc_dead_code(self) -> list[GCFinding]:
        """Detect dead code and entropy."""
        from armature.gc.agents.dead_code import scan_dead_code
        return scan_dead_code(self.root, self.config)

    def _gc_budget(self) -> list[GCFinding]:
        """Audit budget usage across specs."""
        from armature.gc.agents.budget import audit_budgets
        return audit_budgets(self.root, self.config.budget)
