# Changelog

All notable changes to Armature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-04-21

### Added

- **Spec comparison engine**: Compare armature specs against ossature output with structural diff
- **Spec file structure**: Documentation and sample specs for all three example projects
- **Spec output generation**: Generated output artifacts for python-fastapi, typescript-nextjs, and monorepo examples
- **Budget tracking examples**: JSONL cost tracking files with realistic per-request token/cost data across all spec phases
- **Budget reports**: Per-spec, per-project, and cross-project budget summary reports with phase allocation analysis
- **Estimated vs actual cost report**: Cross-project comparison of tier-cap budgets against actual token/cost usage
- **Test cases report**: Cross-project test phase analysis with coverage matrix, quality gates, and test file inventory
- **Blog and social media content**: Medium article, dev.to post, and social media launch content
- **GitHub Pages**: Documentation site at vivekgana.github.io/armature with Mermaid diagram rendering
- **Hero banner**: SVG/PNG banner image for documentation and articles
- **Ossature compatibility bridge**: Bridge layer for ossature integration

### Fixed

- Mermaid diagram rendering on GitHub Pages (explicit `mermaid.run()` with layout override)
- GitHub Pages baseurl configuration for correct asset loading

## [0.1.0] - 2026-04-17

### Added

- **Budget pillar**: Token/cost tracking, optimization, benchmarking, calibration, caching, circuit breaker, routing
- **Quality pillar**: Lint, type check, and test runners with quality gates (draft/review/merge), shift-left post-write checks
- **Architecture pillar**: Layer boundary enforcement, class conformance checks, import and class linters
- **GC pillar**: Garbage collection agents for architecture drift, stale docs, dead code, and budget audits
- **Self-Heal pillar**: Auto-fix pipeline with circuit breaker escalation
- **Context pillar**: Placeholder for CLAUDE.md generation and progressive disclosure
- **CLI**: Commands for `init`, `check`, `heal`, `gc`, `budget`, `hooks`, `report`, `baseline`
- **MCP server**: Model Context Protocol server exposing all pillars as tools
- **IDE integrations**: Claude Code, Cursor, Copilot, Windsurf, GitHub Actions, pre-commit hooks
- **Configuration**: YAML-based config with Pydantic schema validation, auto-discovery, sensible defaults
- **Examples**: FastAPI, Next.js, and monorepo example configurations
- **Claude Code skills**: Slash commands for `/armature-check`, `/armature-heal`, `/armature-gc`, `/armature-budget`
- **Documentation**: Architecture diagrams, installation guide, GitHub setup guide, harness engineering theory

### Security

- All subprocess calls use `shell=False` with list arguments
- Input validation on all user-facing parameters (spec IDs, file paths, tool names)
- Path traversal protection on file operations
- Tool execution restricted to validated allowlist
- Cache integrity verification with SHA-256 checksums

[Unreleased]: https://github.com/vivekgana/armature/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/vivekgana/armature/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/vivekgana/armature/releases/tag/v0.1.0
