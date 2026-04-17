# Installation Guide

Armature can be installed as a **CLI tool**, used as an **MCP server**, or added from **cloud plugin marketplaces**.

---

## Option 1: Install as a CLI Tool

### From PyPI

```bash
pip install armature
```

### From Source

```bash
git clone https://github.com/armature-dev/armature.git
cd armature
pip install -e ".[dev]"
```

### With Optional Dependencies

```bash
# Python quality tools (ruff, mypy, pytest)
pip install armature[python]

# All language support
pip install armature[all]

# Development (includes testing tools)
pip install armature[dev]
```

### Verify Installation

```bash
armature --version
armature --help
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `armature init` | Initialize armature in your project (creates `armature.yaml`) |
| `armature check` | Run quality gates (lint, type check, tests) |
| `armature heal --failures lint` | Auto-fix lint violations |
| `armature gc` | Run garbage collection (dead code, stale docs) |
| `armature budget --spec SPEC-001` | Track token/cost budget |
| `armature budget --report SPEC-001` | Generate budget report |
| `armature hooks --claude-code` | Wire into Claude Code |
| `armature hooks --cursor` | Wire into Cursor |
| `armature report` | Generate project quality report |
| `armature baseline` | Capture project baseline snapshot |

---

## Option 2: Install as an MCP Server

Armature exposes its capabilities via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), allowing AI coding agents to call armature tools directly.

### For Claude Code

Add to your `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "armature": {
      "command": "python",
      "args": ["-m", "armature.mcp.server"],
      "env": {
        "ARMATURE_PROJECT_DIR": "/path/to/your/project"
      }
    }
  }
}
```

Or use the CLI to auto-configure:

```bash
armature hooks --claude-code
```

### For Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "armature": {
      "command": "python",
      "args": ["-m", "armature.mcp.server"],
      "env": {
        "ARMATURE_PROJECT_DIR": "."
      }
    }
  }
}
```

Or use the CLI:

```bash
armature hooks --cursor
```

### For VS Code (Copilot)

Add to `.vscode/settings.json`:

```json
{
  "github.copilot.chat.mcpServers": {
    "armature": {
      "command": "python",
      "args": ["-m", "armature.mcp.server"]
    }
  }
}
```

### For Windsurf

```bash
armature hooks --windsurf
```

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `armature_check` | Run quality sensors and return results |
| `armature_heal` | Run self-healing pipeline |
| `armature_gc` | Run garbage collection sweep |
| `armature_budget_log` | Log token/cost usage |
| `armature_budget_report` | Generate cost report |
| `armature_architecture_check` | Check layer boundaries |
| `armature_baseline` | Capture/compare project baseline |

---

## Option 3: Install from Cloud Plugin Marketplace

### Claude Code MCP Directory

1. Visit the [Claude Code MCP Directory](https://claude.ai/mcp)
2. Search for **"armature"**
3. Click **Install**
4. The MCP server configuration is automatically added to your Claude Code settings
5. Restart Claude Code to activate

### NPM MCP Registry (for global install)

```bash
npx @anthropic-ai/mcp-registry install armature
```

### Smithery.ai Marketplace

1. Visit [smithery.ai](https://smithery.ai/)
2. Search for **"armature"**
3. Click **Install** and select your IDE (Claude Code, Cursor, VS Code)
4. Follow the one-click install instructions

### Glama.ai MCP Directory

1. Visit [glama.ai/mcp](https://glama.ai/mcp)
2. Search for **"armature"**
3. Copy the configuration for your IDE
4. Paste into your MCP settings file

### Manual Registry Configuration

If your marketplace supports MCP registry format, use this manifest:

```json
{
  "name": "armature",
  "description": "Harness engineering framework for AI coding agents",
  "version": "0.1.0",
  "transport": "stdio",
  "command": "python",
  "args": ["-m", "armature.mcp.server"],
  "tools": [
    "armature_check",
    "armature_heal",
    "armature_gc",
    "armature_budget_log",
    "armature_budget_report",
    "armature_architecture_check",
    "armature_baseline"
  ],
  "env": {
    "ARMATURE_PROJECT_DIR": {
      "description": "Path to the project directory",
      "required": false,
      "default": "."
    }
  }
}
```

---

## Option 4: GitHub Actions Integration

Add armature to your CI/CD pipeline:

```bash
armature hooks --github-actions
```

This creates `.github/workflows/armature.yml`:

```yaml
name: Armature Quality Gate

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install armature[python]
      - run: armature check --gate merge
```

---

## Option 5: Pre-commit Hook

```bash
armature hooks --pre-commit
```

This adds to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/armature-dev/armature
    rev: v0.1.0
    hooks:
      - id: armature-check
        name: Armature Quality Gate
        entry: armature check --gate draft
        language: python
        pass_filenames: false
```

---

## Configuration

After installation, initialize armature in your project:

```bash
cd your-project/
armature init
```

This creates `armature.yaml` with sensible defaults. See [README.md](../README.md) for configuration options.

## Upgrading

```bash
# PyPI
pip install --upgrade armature

# From source
git pull origin main
pip install -e ".[dev]"
```

## Uninstalling

```bash
pip uninstall armature

# Remove config files
rm armature.yaml
rm -rf .armature/
```
