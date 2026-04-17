# GitHub Repository Setup Guide

## Prerequisites

- [Git](https://git-scm.com/) installed
- [GitHub CLI (`gh`)](https://cli.github.com/) installed (recommended)
- [Python 3.11+](https://www.python.org/downloads/)
- A GitHub account

## 1. Create the GitHub Repository

### Option A: Using GitHub CLI (recommended)

```bash
cd armature/
git init

# Create a public repository
gh repo create armature-dev/armature --public --source=. --description "Harness engineering framework for AI coding agents"

# Or create a private repository
gh repo create armature-dev/armature --private --source=. --description "Harness engineering framework for AI coding agents"
```

### Option B: Using GitHub Web UI

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `armature`
3. Description: *Harness engineering framework for AI coding agents*
4. Choose Public or Private
5. **Do not** initialize with README (we already have one)
6. Click **Create repository**
7. Follow the instructions to push an existing repository:

```bash
cd armature/
git init
git add .
git commit -m "Initial commit: armature harness engineering framework"
git branch -M main
git remote add origin https://github.com/armature-dev/armature.git
git push -u origin main
```

## 2. Initial Commit

```bash
# Verify .gitignore is in place (filters out __pycache__, .coverage, etc.)
cat .gitignore

# Stage all files
git add .

# Review what will be committed
git status

# Commit
git commit -m "Initial commit: armature harness engineering framework

- 6-pillar architecture: budget, quality, context, architecture, gc, heal
- CLI commands: init, check, heal, gc, budget, hooks, report
- IDE integrations: Claude Code, Cursor, Copilot, Windsurf, GitHub Actions
- MCP server for Model Context Protocol
- Full test suite
- Claude Code skills (slash commands)"
```

## 3. Branch Protection Rules

Go to **Settings > Branches > Add branch protection rule**:

| Setting | Value |
|---------|-------|
| Branch name pattern | `main` |
| Require pull request reviews | Yes (1 reviewer) |
| Require status checks to pass | Yes |
| Required status checks | `test`, `lint`, `type-check` |
| Require branches to be up to date | Yes |
| Include administrators | Yes |

## 4. Set Up GitHub Actions CI

Create the workflow file:

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with ruff
        run: ruff check src/ tests/

      - name: Type check with mypy
        run: mypy src/

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  publish:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build tools
        run: pip install build

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

## 5. Repository Settings

### Topics

Add these topics to make the repository discoverable:

```
ai, coding-agent, harness, quality, architecture, linting, claude-code,
cursor, copilot, mcp, developer-tools, python
```

### About Section

- **Description**: Harness engineering framework for AI coding agents -- the invisible skeleton that shapes agent output
- **Website**: (docs URL when available)

### Labels for Issues

| Label | Color | Description |
|-------|-------|-------------|
| `pillar:budget` | `#0E8A16` | Budget tracking & optimization |
| `pillar:quality` | `#1D76DB` | Quality gates & checks |
| `pillar:architecture` | `#D93F0B` | Architecture enforcement |
| `pillar:gc` | `#FBCA04` | Garbage collection |
| `pillar:heal` | `#5319E7` | Self-healing pipeline |
| `pillar:context` | `#F9D0C4` | Context management |
| `integration` | `#C2E0C6` | IDE & CI integrations |
| `mcp` | `#BFD4F2` | MCP server |

Create labels with GitHub CLI:

```bash
gh label create "pillar:budget" --color "0E8A16" --description "Budget tracking & optimization"
gh label create "pillar:quality" --color "1D76DB" --description "Quality gates & checks"
gh label create "pillar:architecture" --color "D93F0B" --description "Architecture enforcement"
gh label create "pillar:gc" --color "FBCA04" --description "Garbage collection"
gh label create "pillar:heal" --color "5319E7" --description "Self-healing pipeline"
gh label create "pillar:context" --color "F9D0C4" --description "Context management"
gh label create "integration" --color "C2E0C6" --description "IDE & CI integrations"
gh label create "mcp" --color "BFD4F2" --description "MCP server"
```

## 6. Release Workflow

Tag-based releases trigger PyPI publishing:

```bash
# Bump version in pyproject.toml, then:
git add pyproject.toml
git commit -m "release: v0.1.0"
git tag v0.1.0
git push origin main --tags
```

## 7. Development Workflow

```bash
# Clone the repository
git clone https://github.com/armature-dev/armature.git
cd armature

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/

# Create a feature branch
git checkout -b feature/my-feature

# Make changes, then
git add .
git commit -m "feat: description of changes"
git push -u origin feature/my-feature

# Create a pull request
gh pr create --title "feat: description" --body "Summary of changes"
```
