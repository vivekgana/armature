"""Post-write hook runner -- shift-left quality checks on every file write.

This implements the 'shift feedback left' pattern:
run quality checks on the changed file immediately, not at commit time.

Wired into IDE hooks via `armature check --file <path>`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from armature._internal.subprocess_utils import run_tool
from armature.config.loader import load_config_or_defaults


def check_file(file_path: str) -> int:
    """Run post-write checks on a single file.

    Returns 0 if clean, 1 if issues found.
    """
    path = Path(file_path)
    if not path.exists():
        return 0
    if path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        return 0

    config = load_config_or_defaults()
    if not config.quality.post_write.enabled:
        return 0

    root = Path.cwd()
    issues_found = False
    max_lines = config.quality.post_write.max_output_lines

    for tool_name in config.quality.post_write.tools:
        tool_config = config.quality.checks.get(tool_name)
        if tool_config is None:
            continue

        args = [tool_config.tool, *tool_config.args, str(path)]
        result = run_tool(args, cwd=root, timeout=15)

        if not result.ok and result.stdout.strip():
            issues_found = True
            lines = result.stdout.strip().split("\n")
            print(f"[{tool_config.tool}] {path.name}:")
            for line in lines[:max_lines]:
                print(f"  {line}")
            if len(lines) > max_lines:
                print(f"  ... and {len(lines) - max_lines} more")

    return 1 if issues_found else 0


def main() -> int:
    """CLI entry point for post-write hook."""
    if len(sys.argv) < 2:
        print("Usage: python -m armature.quality.post_write <file_path>")
        return 1
    return check_file(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
