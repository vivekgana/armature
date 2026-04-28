# Armature VS Code Extension

Runs [Armature](https://github.com/vivekgana/armature) quality checks on every file save
and displays violations directly in the VS Code **Problems** panel.

## Prerequisites

1. Python ≥ 3.11
2. `armature-harness` installed in your project environment:
   ```bash
   pip install "armature-harness[python]"
   ```

## Features

- **Check on save** — automatically runs `armature check --file <path> --json`
  whenever you save a file and populates the Problems panel.
- **Project-wide check** — run `Armature: Run Quality Check` from the Command Palette.
- **Self-heal** — run `Armature: Self-Heal Failures` to invoke the auto-fix pipeline.
- **Status bar** — shows the current quality score and gate level at a glance.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `armature.checkOnSave` | `true` | Run check on every save |
| `armature.configFile` | `armature.yaml` | Config path relative to workspace root |
| `armature.executablePath` | `armature` | Path to the armature binary |
| `armature.showStatusBar` | `true` | Show score in the status bar |

## Building from Source

```bash
cd vscode-extension
npm install
npm run compile
npm run package   # produces armature-vscode-*.vsix
```

Install the `.vsix` with **Extensions: Install from VSIX…** in the Command Palette.

## Publishing to VS Code Marketplace

```bash
npm install -g @vscode/vsce
vsce login <publisher>
vsce publish
```
