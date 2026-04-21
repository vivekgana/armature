"""armature init -- scaffold armature.yaml for a new project."""

from __future__ import annotations

from pathlib import Path

import click
import yaml

from armature._internal.output import console, print_check
from armature.config.discovery import detect_project


@click.command()
@click.option("--dir", "project_dir", default=".", help="Project root directory")
@click.option("--force", is_flag=True, help="Overwrite existing armature.yaml")
def init_cmd(project_dir: str, force: bool) -> None:
    """Scaffold armature.yaml for a new project (auto-detects language/framework)."""
    root = Path(project_dir).resolve()
    config_path = root / "armature.yaml"

    if config_path.exists() and not force:
        console.print(f"[yellow]armature.yaml already exists at {config_path}[/yellow]")
        console.print("Use --force to overwrite.")
        raise SystemExit(1)

    # Auto-detect project
    detection = detect_project(root)
    console.print("\n[bold]Armature Init[/bold]")
    console.print("=" * 40)
    print_check("Language", True, detection.language)
    print_check("Framework", True, detection.framework or "(none detected)")
    print_check("Source dir", True, detection.src_dir)
    print_check("Test dir", True, detection.test_dir)
    print_check("Lint tool", True, detection.lint_tool)
    print_check("Type checker", True, detection.type_tool)
    print_check("Test runner", True, detection.test_tool)

    # Generate config
    config = _generate_config(detection)

    # Run benchmark to suggest budget tier
    from armature.config.schema import ArmatureConfig, ProjectConfig
    benchmark_config = ArmatureConfig(project=ProjectConfig(
        language=detection.language, framework=detection.framework,
        src_dir=detection.src_dir, test_dir=detection.test_dir,
    ))
    from armature.budget.benchmark import calculate_benchmark, scan_project
    scope = scan_project(root, benchmark_config)
    benchmark = calculate_benchmark(scope)

    print_check("Lines of code", True, f"{scope.total_loc:,}")
    print_check("Budget tier", True, f"{benchmark.recommended_tier} "
                f"({benchmark.recommended_tokens:,} tokens / ${benchmark.recommended_cost_usd:.2f})")

    # Add recommended budget to config
    config["budget"] = {
        "enabled": True,
        "defaults": {
            benchmark.recommended_tier: {
                "max_tokens": benchmark.recommended_tokens,
                "max_cost_usd": benchmark.recommended_cost_usd,
            },
        },
    }

    # Write YAML
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")
    console.print(f"\n[green]Created:[/green] {config_path}")

    # Create storage directory
    storage_dir = root / ".armature"
    storage_dir.mkdir(exist_ok=True)
    (storage_dir / ".gitkeep").touch()
    console.print(f"[green]Created:[/green] {storage_dir}/")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review and customize armature.yaml")
    console.print("  2. Run: armature budget --benchmark   (verify budget fit)")
    console.print("  3. Run: armature hooks --claude-code  (wire into Claude Code)")
    console.print("  4. Run: armature check               (verify setup)")


def _generate_config(detection: detect_project.__class__) -> dict:  # type: ignore[name-defined]
    """Generate armature.yaml content from detection results."""
    config: dict = {
        "project": {
            "name": Path.cwd().name,
            "language": detection.language,
            "src_dir": detection.src_dir,
            "test_dir": detection.test_dir,
        },
        "quality": {
            "enabled": True,
            "gates": {"draft": 0.70, "review_ready": 0.85, "merge_ready": 0.95},
            "checks": {
                "lint": {"tool": detection.lint_tool, "weight": 25},
                "type_check": {"tool": detection.type_tool, "weight": 25},
                "test": {"tool": detection.test_tool, "weight": 20, "coverage_min": 85},
            },
            "post_write": {"enabled": True, "tools": ["lint", "type_check"]},
        },
        "heal": {
            "enabled": True,
            "max_attempts": 3,
            "healers": {
                "lint": {"enabled": True, "auto_fix": True},
                "type_check": {"enabled": True, "auto_fix": False},
                "test": {"enabled": True, "auto_fix": False},
            },
        },
        "integrations": {
            "claude_code": {"enabled": True, "post_tool_use": True, "pre_session": True},
        },
    }

    if detection.framework:
        config["project"]["framework"] = detection.framework

    return config
