"""armature report -- generate full harness report."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import click

from armature._internal.output import console, print_header
from armature.config.loader import load_config_or_defaults


@click.command()
@click.option("--spec", "spec_id", help="Spec ID to include in report")
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--html", "use_html", is_flag=True, help="Output as a self-contained HTML report")
@click.option("--output", "output_path", default=None, help="Write output to this file path")
def report_cmd(spec_id: str | None, use_json: bool, use_html: bool, output_path: str | None) -> None:
    """Generate full harness report (quality score, budget, compliance)."""
    config = load_config_or_defaults()
    root = Path.cwd()

    report: dict = {"sections": []}

    # Quality section
    if config.quality.enabled:
        from armature.quality.scorer import run_quality_checks
        results = run_quality_checks(config.quality, root)
        score = sum(r.score for r in results) / len(results) if results else 1.0
        report["sections"].append({
            "name": "quality",
            "score": round(score, 2),
            "checks": [{"name": r.name, "passed": r.passed, "violations": r.violation_count} for r in results],
        })

    # Architecture section
    if config.architecture.enabled:
        from armature.architecture.boundary import run_boundary_check
        from armature.architecture.conformance import run_conformance_check
        boundary = run_boundary_check(config.architecture, root)
        conform = run_conformance_check(config.architecture, root)
        report["sections"].append({
            "name": "architecture",
            "boundary_violations": boundary.violation_count,
            "conformance_violations": conform.violation_count,
        })

    # Budget section
    if config.budget.enabled and spec_id:
        from armature.budget.tracker import SessionTracker
        tracker = SessionTracker(config.budget)
        usage = tracker.get_usage(spec_id)
        report["sections"].append({"name": "budget", "spec_id": spec_id, **usage})

    if use_html:
        content = _render_html(report, config.project.name or root.name)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(content, encoding="utf-8")
            console.print(f"[green]Report written:[/green] {output_path}")
        else:
            click.echo(content)
        return

    if use_json:
        json_content = json.dumps(report, indent=2)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(json_content, encoding="utf-8")
            console.print(f"[green]Report written:[/green] {output_path}")
        else:
            click.echo(json_content)
        return

    print_header("Armature Harness Report")
    for section in report["sections"]:
        console.print(f"\n  [bold]{section['name'].upper()}[/bold]")
        for key, value in section.items():
            if key != "name":
                console.print(f"    {key}: {value}")


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _render_html(report: dict, project_name: str) -> str:
    """Render the report dict as a self-contained HTML page."""
    generated_at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")

    sections_html = ""
    for section in report.get("sections", []):
        name = section.get("name", "unknown").upper()
        if section["name"] == "quality":
            score = section.get("score", 0)
            pct = int(score * 100)
            gate = "merge_ready" if score >= 0.95 else "review_ready" if score >= 0.85 else "draft"
            gate_color = "#22c55e" if gate == "merge_ready" else "#f59e0b" if gate == "review_ready" else "#ef4444"
            rows = ""
            for check in section.get("checks", []):
                status = "✅" if check["passed"] else "❌"
                rows += (
                    f"<tr><td>{check['name']}</td>"
                    f"<td style='text-align:center'>{status}</td>"
                    f"<td>{check['violations']}</td></tr>"
                )
            sections_html += f"""
<section>
  <h2>{name}</h2>
  <p>Score: <strong>{pct}%</strong>
     <span style="background:{gate_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.85em">{gate}</span>
  </p>
  <table>
    <thead><tr><th>Check</th><th>Status</th><th>Violations</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""
        else:
            items = "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in section.items() if k != "name"
            )
            sections_html += f"""
<section>
  <h2>{name}</h2>
  <table><thead><tr><th>Key</th><th>Value</th></tr></thead>
  <tbody>{items}</tbody></table>
</section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Armature Report — {project_name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto;
            padding: 0 20px; color: #1a1a1a; background: #f9fafb; }}
    h1   {{ color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
    h2   {{ color: #334155; margin-top: 32px; }}
    section {{ background: #fff; border-radius: 8px; padding: 20px; margin: 16px 0;
               box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    footer {{ color: #94a3b8; font-size: 0.85em; margin-top: 32px; text-align: center; }}
  </style>
</head>
<body>
  <h1>Armature Quality Report</h1>
  <p><strong>Project:</strong> {project_name} &nbsp;·&nbsp;
     <strong>Generated:</strong> {generated_at}</p>
  {sections_html}
  <footer>Generated by <a href="https://github.com/vivekgana/armature">Armature</a></footer>
</body>
</html>
"""

