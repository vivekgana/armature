# Contributing to Armature

Thank you for your interest in contributing to Armature! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/vivekgana/armature.git
cd armature

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode with all extras
pip install -e ".[dev]"

# Verify everything works
make test
make lint
make typecheck
```

## Development Workflow

1. **Fork** the repository on GitHub
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with tests
4. **Run the full check suite**:
   ```bash
   make check
   ```
5. **Commit** with a clear message (see [Commit Messages](#commit-messages))
6. **Push** to your fork and open a **Pull Request**

## Running Tests

```bash
# Run all tests with coverage
make test

# Run a specific test file
pytest tests/test_budget/test_tracker.py -v

# Run tests matching a keyword
pytest -k "test_boundary" -v

# Run with verbose output
pytest -v --tb=long
```

## Code Quality

All code must pass these checks before merging:

```bash
# Lint (ruff)
make lint

# Type check (mypy)
make typecheck

# Format check
make format-check

# Run everything at once
make check
```

## Project Structure

```
src/
├── _internal/        # Shared utilities
├── architecture/     # Layer boundary enforcement
├── budget/           # Token/cost tracking
├── cli/              # CLI commands (Click)
├── config/           # Configuration schema & loading
├── context/          # Context management
├── gc/               # Garbage collection
├── harness/          # Session lifecycle hooks
├── heal/             # Self-healing pipeline
├── integrations/     # IDE integrations
├── mcp/              # MCP server
├── quality/          # Quality gates & scoring
└── spec/             # Spec-driven development
```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add token usage histogram to budget report`
- `fix: boundary checker missing transitive dependencies`
- `docs: add MCP server configuration examples`
- `test: add edge cases for circuit breaker escalation`
- `refactor: simplify config loader discovery logic`

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if behavior changes
- Ensure all CI checks pass
- Link related issues in the PR description

## Adding a New Pillar Module

1. Create the module under `src/` (e.g., `src/my_pillar/`)
2. Add `__init__.py` with public exports
3. Create a CLI command in `src/cli/my_pillar_cmd.py`
4. Register the command in `src/cli/main.py`
5. Add tests under `tests/test_my_pillar/`
6. Update `docs/ARCHITECTURE.md` with the new module
7. Add a Claude Code skill in `skills/` if applicable

## Adding an IDE Integration

1. Create the integration in `src/integrations/`
2. Add a `--my-ide` flag to `src/cli/hooks_cmd.py`
3. Add tests in `tests/test_integrations/`
4. Document in `docs/INSTALLATION.md`

## Reporting Bugs

Open an issue using the **Bug Report** template. Include:

- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant `armature.yaml` configuration

## Requesting Features

Open an issue using the **Feature Request** template. Describe:

- The use case and motivation
- How it fits into the 6-pillar model
- Any proposed API or CLI interface

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
