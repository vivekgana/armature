"""CLI commands for Agent Arena and SWE-bench correlation benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

import click

from armature._internal.output import console


@click.group()
def benchmark_cmd() -> None:
    """Benchmark AI coding agents with Armature governance."""


@benchmark_cmd.command("arena")
@click.option("--agents", default=None, help="Comma-separated agent names (default: all)")
@click.option("--categories", default=None, help="Comma-separated task categories")
@click.option("--replay-dir", default=None, type=click.Path(), help="Replay directory")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output JSON path")
def arena_cmd(agents: str | None, categories: str | None, replay_dir: str | None, output: str | None) -> None:
    """Run Agent Arena benchmark across AI coding agents."""
    from armature.benchmark.arena import AgentArena
    from armature.benchmark.reporter import BenchmarkReporter
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    arena = AgentArena(config)

    agent_list = agents.split(",") if agents else None
    category_set = set(categories.split(",")) if categories else None

    replay_path = Path(replay_dir) if replay_dir else None

    console.print("[bold]ARMATURE AGENT ARENA[/bold]")
    console.print(f"  Tasks: {len(arena.suite.tasks)}")
    console.print(f"  Agents: {agent_list or list(arena.suite.agents.keys())}")
    console.print("")

    results = arena.run_all(agents=agent_list, categories=category_set, replay_dir=replay_path)

    reporter = BenchmarkReporter()
    console.print(reporter.format_arena_results(results))
    console.print("")
    console.print(reporter.format_per_task_breakdown(results))

    if output:
        export = reporter.export_json(arena_results=results)
        Path(output).write_text(json.dumps(export, indent=2), encoding="utf-8")
        console.print(f"\n  Results saved to: {output}")


@benchmark_cmd.command("correlation")
@click.option("--dataset", default="swebench-lite", help="Dataset: swebench-lite")
@click.option("--replay-dir", default=None, type=click.Path(), help="Replay directory with results")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output JSON path")
def correlation_cmd(dataset: str, replay_dir: str | None, output: str | None) -> None:
    """Analyze quality-correctness correlation (SWE-bench style)."""
    from armature.benchmark.correlation import QualityCorrelation
    from armature.benchmark.reporter import BenchmarkReporter
    from armature.benchmark.runner import BenchmarkRunner
    from armature.benchmark.tasks import load_swebench_dataset
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()

    dataset_path = Path(f"data/{dataset.replace('-', '_')}_correlation.yaml")
    if not dataset_path.exists():
        dataset_path = Path("data/swebench_correlation.yaml")

    swebench = load_swebench_dataset(dataset_path)

    console.print("[bold]SWE-BENCH QUALITY CORRELATION ANALYSIS[/bold]")
    console.print(f"  Dataset: {swebench.name} v{swebench.version}")
    console.print(f"  Tasks: {len(swebench.tasks)}")
    console.print("")

    runner = BenchmarkRunner(config)
    replay_path = Path(replay_dir) if replay_dir else None

    # Load task results from replay or generate synthetic for demonstration
    from armature.benchmark.tasks import BenchmarkTask
    task_results = []
    for task in swebench.tasks:
        bt = BenchmarkTask(
            id=task.task_id, category=task.category,
            description=task.description, difficulty=task.difficulty,
            language=task.language, estimated_tokens=task.estimated_tokens,
            verification="",
        )
        result = runner.run_task(bt, agent="evaluation", replay_dir=replay_path)
        task_results.append(result)

    if not task_results:
        console.print("  [yellow]No task results available. Use --replay-dir with recorded results.[/yellow]")
        return

    correlation = QualityCorrelation(task_results)
    corr_result = correlation.compute()

    reporter = BenchmarkReporter()
    console.print(reporter.format_correlation_report(corr_result))

    if output:
        export = reporter.export_json(correlation_result=corr_result)
        Path(output).write_text(json.dumps(export, indent=2), encoding="utf-8")
        console.print(f"\n  Results saved to: {output}")


@benchmark_cmd.command("report")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output file path")
def report_cmd(fmt: str, output: str | None) -> None:
    """Generate combined benchmark report."""
    from armature.config.loader import load_config_or_defaults

    config = load_config_or_defaults()
    output_dir = Path(config.benchmark.output_dir)

    if fmt == "json":
        # Load latest results from output dir
        results: dict[str, object] = {}
        arena_file = output_dir / "arena_latest.json"
        if arena_file.exists():
            results["arena"] = json.loads(arena_file.read_text(encoding="utf-8"))
        corr_file = output_dir / "correlation_latest.json"
        if corr_file.exists():
            results["correlation"] = json.loads(corr_file.read_text(encoding="utf-8"))

        text = json.dumps(results, indent=2)
    else:
        text = "Run 'armature benchmark arena' or 'armature benchmark correlation' first."

    if output:
        Path(output).write_text(text, encoding="utf-8")
        console.print(f"Report saved to: {output}")
    else:
        console.print(text)
