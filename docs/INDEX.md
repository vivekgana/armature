# Armature Documentation

## Getting Started

- [Installation Guide](INSTALLATION.md) -- CLI install, MCP server setup, marketplace plugins
- [GitHub Repository Setup](GITHUB_SETUP.md) -- Create the repo, CI/CD, branch protection
- [Architecture Overview](ARCHITECTURE.md) -- Repository structure, component diagrams, data flow

## Design Documents

- [Harness Engineering](HARNESS_ENGINEERING.md) -- Theory and principles behind armature
- [Benchmarking Design](BENCHMARKING_DESIGN.md) -- Performance benchmarking system design
- [Spec-Driven Development](SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md) -- Guidelines for spec-driven workflows

## Pillar Guides

| Pillar | Description |
|--------|-------------|
| Budget | Token/cost tracking, optimization, calibration |
| Quality | Lint, type, test checks with quality gates |
| Context | CLAUDE.md generation, progressive disclosure |
| Architecture | Layer boundaries, class conformance |
| GC | Dead code, stale docs, architecture drift |
| Self-Heal | Auto-fix lint, circuit breaker escalation |

## Integration Guides

Armature integrates with the following IDEs and CI systems (see [INSTALLATION.md](INSTALLATION.md)):

- Claude Code
- Cursor
- GitHub Copilot
- Windsurf
- GitHub Actions
- Pre-commit hooks

## Examples

See the [examples/](../examples/) directory for complete project setups:

- `python-fastapi/` -- FastAPI project with armature
- `typescript-nextjs/` -- Next.js project with armature
- `monorepo/` -- Monorepo with multiple packages

## Claude Code Skills

Armature provides slash commands for Claude Code. See [skills/](../skills/):

- `/armature-check` -- Run quality sensors
- `/armature-heal` -- Self-healing pipeline
- `/armature-gc` -- Garbage collection sweep
- `/armature-budget` -- Cost tracking and reporting
