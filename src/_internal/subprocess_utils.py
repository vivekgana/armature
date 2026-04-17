"""Safe subprocess runner with timeout and output capture."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    """Result of a subprocess execution."""
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_tool(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
    capture: bool = True,
) -> RunResult:
    """Run a subprocess safely with timeout.

    Args:
        args: Command and arguments.
        cwd: Working directory.
        timeout: Timeout in seconds.
        capture: Whether to capture stdout/stderr.

    Returns:
        RunResult with return code and captured output.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=capture,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
        )
        return RunResult(
            returncode=result.returncode,
            stdout=result.stdout if capture else "",
            stderr=result.stderr if capture else "",
        )
    except FileNotFoundError:
        return RunResult(returncode=-1, stdout="", stderr=f"Command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        return RunResult(returncode=-2, stdout="", stderr=f"Command timed out after {timeout}s: {' '.join(args)}")
