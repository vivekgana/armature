"""Tests for _internal/subprocess_utils.py -- safe subprocess runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature._internal.subprocess_utils import RunResult, run_tool


class TestRunResult:
    """Tests for RunResult dataclass."""

    def test_ok_property(self):
        assert RunResult(returncode=0, stdout="", stderr="").ok is True
        assert RunResult(returncode=1, stdout="", stderr="").ok is False
        assert RunResult(returncode=-1, stdout="", stderr="").ok is False


class TestRunTool:
    """Tests for run_tool() subprocess wrapper."""

    def test_successful_command(self):
        result = run_tool(["python", "--version"])
        assert result.ok is True
        assert "python" in result.stdout.lower() or "python" in result.stderr.lower()

    def test_command_not_found(self):
        result = run_tool(["nonexistent_command_12345"])
        assert result.ok is False
        assert result.returncode == -1
        assert "not found" in result.stderr.lower()

    def test_timeout(self):
        result = run_tool(["python", "-c", "import time; time.sleep(10)"], timeout=1)
        assert result.ok is False
        assert result.returncode == -2
        assert "timed out" in result.stderr.lower()

    def test_captures_stdout(self):
        result = run_tool(["python", "-c", "print('hello')"])
        assert result.ok is True
        assert "hello" in result.stdout
