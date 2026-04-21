"""Request planner -- pre-build analysis and per-task batching.

Works with the pre-planning model: given a complete build plan, produces
optimal request groupings for EVERY task upfront. The same batching strategy
applies to all tasks -- no progressive degradation.

Token waste in AI coding sessions comes from:
1. Sequential single-file reads (each carries conversation context overhead)
2. Re-reading files already in context
3. Sending full codebase when only 3 files are relevant
4. Not leveraging prompt caching (5-min TTL)

The planner addresses each by analyzing ALL tasks before execution starts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from armature.budget.optimizer import (
    TOKENS_PER_CHAR,
    TaskSpec,
)


@dataclass
class FileGroup:
    """A group of files to read in a single request."""
    files: list[str]
    estimated_tokens: int
    reason: str  # "same_module", "dependency_chain", "shared_context"


@dataclass
class TaskRequestPlan:
    """Request plan for a single task."""
    task_id: str
    groups: list[FileGroup]
    total_estimated_tokens: int
    total_requests: int
    savings_vs_sequential: int
    shared_files: list[str]  # files shared with other tasks (cache-friendly)


@dataclass
class BuildRequestPlan:
    """Complete request plan for an entire build -- all tasks planned upfront."""
    spec_id: str
    task_plans: list[TaskRequestPlan]
    total_estimated_tokens: int
    total_requests: int
    total_savings: int
    shared_context_files: list[str]  # files used by 2+ tasks (prime for caching)
    execution_order: list[str]  # recommended task execution order for cache hits


@dataclass
class TaskContext:
    """Context needed for a single build task (legacy compat)."""
    spec_refs: list[str] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    verify_command: str = ""


class RequestPlanner:
    """Plans optimal request sequences for entire builds.

    Analyzes ALL tasks upfront to:
    - Identify shared files across tasks (maximize prompt cache hits)
    - Order task execution for cache locality
    - Batch file reads within each task
    - Produce uniform per-task request plans
    """

    def __init__(self, root: Path | None = None, max_tokens_per_request: int = 100_000) -> None:
        self.root = root or Path.cwd()
        self.max_tokens_per_request = max_tokens_per_request
        self._file_token_cache: dict[str, int] = {}

    def estimate_file_tokens(self, file_path: str) -> int:
        """Estimate tokens for a file, with caching."""
        if file_path in self._file_token_cache:
            return self._file_token_cache[file_path]

        path = self.root / file_path
        if not path.exists():
            return 0

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tokens = int(len(content) * TOKENS_PER_CHAR)
        except OSError:
            tokens = 5000

        self._file_token_cache[file_path] = tokens
        return tokens

    def plan_build(self, spec_id: str, tasks: list[TaskSpec]) -> BuildRequestPlan:
        """Plan request batching for an entire build -- all tasks at once.

        This is the primary method. Analyzes all tasks to find shared files,
        determine optimal execution order, and produce per-task request plans.
        """
        if not tasks:
            return BuildRequestPlan(
                spec_id=spec_id, task_plans=[], total_estimated_tokens=0,
                total_requests=0, total_savings=0, shared_context_files=[],
                execution_order=[],
            )

        # Step 1: Identify files shared across tasks (cache candidates)
        file_usage: dict[str, list[str]] = {}  # file -> [task_ids using it]
        for task in tasks:
            for f in set(task.context_files + task.spec_refs):
                file_usage.setdefault(f, []).append(task.task_id)

        shared_files = sorted(
            [f for f, task_ids in file_usage.items() if len(task_ids) >= 2],
            key=lambda f: len(file_usage[f]),
            reverse=True,
        )

        # Step 2: Determine execution order for cache locality
        # Tasks that share the most files should run consecutively
        execution_order = self._optimize_execution_order(tasks, file_usage)

        # Step 3: Plan each task
        task_plans = []
        total_tokens = 0
        total_requests = 0
        total_savings = 0

        for task in tasks:
            plan = self._plan_single_task(task, shared_files)
            task_plans.append(plan)
            total_tokens += plan.total_estimated_tokens
            total_requests += plan.total_requests
            total_savings += plan.savings_vs_sequential

        return BuildRequestPlan(
            spec_id=spec_id,
            task_plans=task_plans,
            total_estimated_tokens=total_tokens,
            total_requests=total_requests,
            total_savings=total_savings,
            shared_context_files=shared_files,
            execution_order=execution_order,
        )

    def plan_task(self, task: TaskContext, description: str = "") -> TaskRequestPlan:
        """Plan a single task (convenience wrapper for legacy TaskContext)."""
        spec = TaskSpec(
            task_id=description or "task",
            description=description,
            context_files=task.context_files,
            spec_refs=task.spec_refs,
            output_files=task.output_files,
            verify_command=task.verify_command,
        )
        return self._plan_single_task(spec, shared_files=[])

    def _plan_single_task(
        self,
        task: TaskSpec,
        shared_files: list[str],
    ) -> TaskRequestPlan:
        """Plan request batching for one task."""
        all_files = list(set(task.context_files + task.spec_refs))
        if not all_files:
            return TaskRequestPlan(
                task_id=task.task_id, groups=[], total_estimated_tokens=0,
                total_requests=0, savings_vs_sequential=0, shared_files=[],
            )

        file_sizes = {f: self.estimate_file_tokens(f) for f in all_files}
        total_tokens = sum(file_sizes.values())
        task_shared = [f for f in all_files if f in shared_files]

        # Group: shared files first (cache-friendly), then by directory
        groups: list[FileGroup] = []

        # Group 1: shared files (these benefit from prompt caching)
        if task_shared:
            shared_group_files: list[str] = []
            shared_tokens = 0
            for f in sorted(task_shared, key=lambda x: file_sizes.get(x, 0)):
                f_tokens = file_sizes.get(f, 0)
                if shared_tokens + f_tokens > self.max_tokens_per_request and shared_group_files:
                    groups.append(FileGroup(
                        files=shared_group_files,
                        estimated_tokens=shared_tokens,
                        reason="shared_context",
                    ))
                    shared_group_files = []
                    shared_tokens = 0
                shared_group_files.append(f)
                shared_tokens += f_tokens
            if shared_group_files:
                groups.append(FileGroup(
                    files=shared_group_files,
                    estimated_tokens=shared_tokens,
                    reason="shared_context",
                ))

        # Group 2+: remaining files by directory
        remaining = [f for f in all_files if f not in task_shared]
        dir_groups: dict[str, list[str]] = {}
        for f in remaining:
            dir_key = str(Path(f).parent)
            dir_groups.setdefault(dir_key, []).append(f)

        for dir_path, files in sorted(dir_groups.items()):
            current_group: list[str] = []
            current_tokens = 0
            for f in sorted(files, key=lambda x: file_sizes.get(x, 0)):
                f_tokens = file_sizes.get(f, 0)
                if current_tokens + f_tokens > self.max_tokens_per_request and current_group:
                    groups.append(FileGroup(
                        files=current_group,
                        estimated_tokens=current_tokens,
                        reason=f"same_module:{dir_path}",
                    ))
                    current_group = []
                    current_tokens = 0
                current_group.append(f)
                current_tokens += f_tokens
            if current_group:
                groups.append(FileGroup(
                    files=current_group,
                    estimated_tokens=current_tokens,
                    reason=f"same_module:{dir_path}",
                ))

        # Savings calculation
        CONTEXT_OVERHEAD_PER_REQUEST = 2000
        sequential_cost = total_tokens + len(all_files) * CONTEXT_OVERHEAD_PER_REQUEST
        batched_cost = total_tokens + len(groups) * CONTEXT_OVERHEAD_PER_REQUEST
        savings = sequential_cost - batched_cost

        return TaskRequestPlan(
            task_id=task.task_id,
            groups=groups,
            total_estimated_tokens=total_tokens,
            total_requests=len(groups),
            savings_vs_sequential=savings,
            shared_files=task_shared,
        )

    def _optimize_execution_order(
        self,
        tasks: list[TaskSpec],
        file_usage: dict[str, list[str]],
    ) -> list[str]:
        """Order tasks so consecutive tasks share the most files.

        This maximizes prompt cache hits: the 5-minute TTL means files
        loaded for task N are still cached when task N+1 starts if they
        share files and execute within 5 minutes.
        """
        if len(tasks) <= 1:
            return [t.task_id for t in tasks]

        # Build affinity matrix: how many files do tasks share?
        task_files = {t.task_id: set(t.context_files + t.spec_refs) for t in tasks}
        remaining = list(task_files.keys())
        ordered: list[str] = []

        # Greedy nearest-neighbor: start with largest task, always pick
        # the next task that shares the most files with current
        current = max(remaining, key=lambda tid: len(task_files[tid]))
        ordered.append(current)
        remaining.remove(current)

        while remaining:
            current_files = task_files[current]
            best = max(remaining, key=lambda tid: len(current_files & task_files[tid]))
            ordered.append(best)
            remaining.remove(best)
            current = best

        return ordered

    def analyze_imports(self, file_path: str) -> list[str]:
        """Extract local imports from a Python file to build dependency chain."""
        path = self.root / file_path
        if not path.exists() or path.suffix != ".py":
            return []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        imports = []
        for line in content.split("\n"):
            match = re.match(r"^\s*(?:from|import)\s+([\w.]+)", line)
            if match:
                module = match.group(1)
                rel_path = module.replace(".", "/") + ".py"
                if (self.root / rel_path).exists():
                    imports.append(rel_path)
                pkg_path = module.replace(".", "/") + "/__init__.py"
                if (self.root / pkg_path).exists():
                    imports.append(pkg_path)

        return imports

    def expand_context(self, task: TaskContext, depth: int = 1) -> TaskContext:
        """Expand task context by following imports to depth N."""
        all_files = set(task.context_files)
        frontier = set(task.context_files)

        for _ in range(depth):
            next_frontier: set[str] = set()
            for f in frontier:
                deps = self.analyze_imports(f)
                for dep in deps:
                    if dep not in all_files:
                        next_frontier.add(dep)
                        all_files.add(dep)
            frontier = next_frontier
            if not frontier:
                break

        return TaskContext(
            spec_refs=task.spec_refs,
            context_files=sorted(all_files),
            output_files=task.output_files,
            verify_command=task.verify_command,
        )

    def format_build_plan(self, plan: BuildRequestPlan) -> str:
        """Format a full build request plan as human-readable text."""
        lines = []
        lines.append(f"BUILD REQUEST PLAN: {plan.spec_id}")
        lines.append(f"  Total tasks:    {len(plan.task_plans)}")
        lines.append(f"  Total requests: {plan.total_requests} "
                      f"(vs {sum(sum(len(g.files) for g in tp.groups) for tp in plan.task_plans)} sequential)")
        lines.append(f"  Total tokens:   {plan.total_estimated_tokens:,}")
        lines.append(f"  Total savings:  {plan.total_savings:,} tokens from batching")

        if plan.shared_context_files:
            lines.append(f"\n  Shared files (cached across tasks): {len(plan.shared_context_files)}")
            for f in plan.shared_context_files[:10]:
                lines.append(f"    - {f}")
            if len(plan.shared_context_files) > 10:
                lines.append(f"    ... and {len(plan.shared_context_files) - 10} more")

        if plan.execution_order:
            lines.append("\n  Recommended execution order (cache-optimized):")
            for i, tid in enumerate(plan.execution_order, 1):
                lines.append(f"    {i}. {tid}")

        lines.append("")
        for tp in plan.task_plans:
            lines.append(f"  Task: {tp.task_id}")
            if tp.shared_files:
                lines.append(f"    Shared (cached): {len(tp.shared_files)} files")
            for j, group in enumerate(tp.groups, 1):
                lines.append(f"    Request {j}: [{group.reason}] ~{group.estimated_tokens:,} tokens")
                for f in group.files:
                    lines.append(f"      - {f}")
            lines.append("")

        return "\n".join(lines)

    def format_plan(self, plan: TaskRequestPlan) -> str:
        """Format a single task request plan (legacy compat)."""
        lines = []
        lines.append(f"Request Plan: {plan.task_id}")
        lines.append(f"Total requests: {plan.total_requests}")
        lines.append(f"Estimated tokens: {plan.total_estimated_tokens:,}")
        if plan.savings_vs_sequential > 0:
            lines.append(f"Savings from batching: {plan.savings_vs_sequential:,} tokens")
        lines.append("")

        for i, group in enumerate(plan.groups, 1):
            lines.append(f"  Request {i}: [{group.reason}] ~{group.estimated_tokens:,} tokens")
            for f in group.files:
                lines.append(f"    - {f}")

        return "\n".join(lines)
