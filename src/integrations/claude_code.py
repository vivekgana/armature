"""Generate .claude/settings.local.json hooks from armature.yaml.

Wires Armature into Claude Code's hook system:
- PostToolUse: shift-left quality check on every file write
- PreSession: environment validation at session start
"""

from __future__ import annotations

import json
from pathlib import Path

from armature.config.schema import ArmatureConfig


def generate_claude_code_hooks(config: ArmatureConfig) -> Path:
    """Generate .claude/settings.local.json with Armature hooks."""
    root = Path.cwd()
    claude_dir = root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings_path = claude_dir / "settings.local.json"

    # Load existing settings if present
    existing: dict = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    hooks: dict = existing.get("hooks", {})
    permissions: list = existing.get("permissions", {}).get("allow", [])

    # PostToolUse hook for shift-left quality checks
    if config.integrations.claude_code.post_tool_use:
        post_tool_hooks = hooks.get("PostToolUse", [])
        armature_hook = {
            "matcher": "Write|Edit",
            "command": "armature check --file $TOOL_INPUT_FILE_PATH",
            "description": "Armature: shift-left quality check on file write",
        }
        # Replace existing Armature hook or add new one
        post_tool_hooks = [h for h in post_tool_hooks if "armature" not in h.get("command", "").lower()
                           and "Armature" not in h.get("description", "")]
        post_tool_hooks.append(armature_hook)
        hooks["PostToolUse"] = post_tool_hooks

    # PreSession hook for environment validation
    if config.integrations.claude_code.pre_session:
        pre_session_hooks = hooks.get("PreSession", [])
        armature_hook = {
            "command": "armature pre-dev --env-check-only",
            "description": "Armature: environment validation at session start",
        }
        pre_session_hooks = [h for h in pre_session_hooks if "armature" not in h.get("command", "").lower()
                             and "Armature" not in h.get("description", "")]
        pre_session_hooks.append(armature_hook)
        hooks["PreSession"] = pre_session_hooks

    # Add permissions for armature commands
    armature_permissions = [
        "Bash(armature check *)",
        "Bash(armature heal *)",
        "Bash(armature gc *)",
        "Bash(armature budget *)",
        "Bash(armature baseline *)",
        "Bash(armature pre-dev *)",
        "Bash(armature post-dev *)",
    ]
    for perm in armature_permissions:
        if perm not in permissions:
            permissions.append(perm)

    settings = {**existing, "hooks": hooks, "permissions": {"allow": permissions}}
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path
