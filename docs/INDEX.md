# Armature Documentation

## Getting Started

- [Installation Guide](INSTALLATION.md) -- CLI install, MCP server setup, marketplace plugins
- [GitHub Repository Setup](GITHUB_SETUP.md) -- Create the repo, CI/CD, branch protection
- [Architecture Overview](ARCHITECTURE.md) -- Repository structure, component diagrams, data flow

## Design Documents

- [Harness Engineering](HARNESS_ENGINEERING.md) -- Theory and principles behind armature
- [Benchmarking Design](BENCHMARKING_DESIGN.md) -- Performance benchmarking system design
- [Spec-Driven Development](SPEC_DRIVEN_DEVELOPMENT_GUIDELINES.md) -- Guidelines for spec-driven workflows

## Pillar Deep Dives (Unique Features)

| Pillar | Description | Guide |
|--------|-------------|-------|
| Budget | Multi-provider routing, per-spec tracking, auto-calibration, circuit breakers | [MULTI_PROVIDER_BUDGET.md](MULTI_PROVIDER_BUDGET.md) |
| Quality | 8 weighted checks with quality gates (lint, type, test, security, complexity, deps, docstring, ratio) | — |
| Context | CLAUDE.md generation, progressive disclosure, cross-session memory, token optimization | [CONTEXT_ENGINEERING.md](CONTEXT_ENGINEERING.md) |
| Architecture | Layer boundaries, class conformance, schema sync | — |
| GC | Dead code, stale docs, architecture drift, budget audit | — |
| Self-Heal | Auto-fix lint, 3-attempt retry, circuit breaker escalation, failure reports | [SELF_HEALING_PIPELINE.md](SELF_HEALING_PIPELINE.md) |

## Integration Guide — 5 AI Coding Agents

Comprehensive setup for all supported IDEs and CI systems:

- [IDE_INTEGRATION_GUIDE.md](IDE_INTEGRATION_GUIDE.md) -- Claude Code, Cursor, Copilot, Windsurf, GitHub Actions
- [INSTALLATION.md](INSTALLATION.md) -- CLI install, MCP server setup, marketplace plugins

Supported agents:
- **Claude Code** -- deepest integration (hooks + MCP + 13 tools + permissions)
- **Cursor** -- rules file + MCP server
- **GitHub Copilot** -- instructions file + VS Code MCP
- **Windsurf** -- rules file
- **GitHub Actions** -- CI workflow generator

## Examples & Reports

- [Sample Project Report](examples/SAMPLE_PROJECT_REPORT.md) -- Full example of quality, budget, self-healing, and benchmark reports for an enterprise project
- See the [examples/](../examples/) directory for complete project setups

## Claude Code Skills

Armature provides slash commands for Claude Code. See [skills/](../skills/):

- `/armature-check` -- Run quality sensors
- `/armature-heal` -- Self-healing pipeline
- `/armature-gc` -- Garbage collection sweep
- `/armature-budget` -- Cost tracking and reporting
