# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in Armature, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. **Email**: Send a detailed report to **armature-security@proton.me**
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgement**: Within 48 hours of your report
- **Assessment**: Within 7 days, we will assess the severity and impact
- **Fix timeline**: Critical/High severity issues will be patched within 14 days
- **Disclosure**: We follow coordinated disclosure -- we will credit you (unless you prefer anonymity) and publish a security advisory once the fix is released

## Security Considerations

Armature is a developer tool that executes commands on behalf of the user. Key security properties:

### Configuration-Driven Execution

Armature executes tools defined in `armature.yaml` (e.g., `ruff`, `mypy`, `pytest`). Only tools from a validated allowlist are permitted. The configuration file should be treated as trusted code -- review `armature.yaml` in any project before running `armature check` or `armature heal`.

### MCP Server

The MCP server (`python -m armature.mcp.server`) communicates over stdio and is designed to be invoked by a trusted AI coding agent (Claude Code, Cursor, etc.). It validates all inputs against JSON schemas before dispatch. File path arguments are constrained to the project root to prevent path traversal.

### Subprocess Execution

All subprocess calls use `shell=False` (list arguments, never string interpolation). Timeouts are enforced on all subprocess invocations to prevent hangs.

### File Operations

- Spec IDs and identifiers used in filenames are validated against a strict alphanumeric pattern
- Cache files are written with restricted permissions (owner-only)
- Atomic writes are used for critical data files to prevent corruption

### What Armature Does NOT Do

- Does not make network requests (no telemetry, no phone-home)
- Does not access credentials or secrets
- Does not modify source code (read-only analysis, except `armature heal` which invokes configured fixers)
- Does not require elevated privileges
