"""Rich console output helpers for Armature CLI."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

console = Console()


def print_header(title: str) -> None:
    """Print a section header."""
    console.print(f"\n[bold]{title}[/bold]")
    console.print("=" * len(title))


def print_check(name: str, passed: bool, detail: str = "") -> None:
    """Print a check result line."""
    icon = "[green]OK[/green]" if passed else "[red]FAIL[/red]"
    line = f"  [{icon}] {name:<25s}"
    if detail:
        line += f" {detail}"
    console.print(line)


def print_violation(file: str, message: str, remediation: str) -> None:
    """Print a violation with remediation."""
    console.print(f"\n[red]VIOLATION:[/red] {file}")
    console.print(f"  {message}")
    console.print(f"  [yellow]FIX:[/yellow] {remediation}")


def make_table(title: str, columns: list[str]) -> Table:
    """Create a Rich table with standard styling."""
    table = Table(title=title, show_header=True, header_style="bold")
    for col in columns:
        table.add_column(col)
    return table
