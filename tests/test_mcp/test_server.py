"""Tests for mcp/server.py -- MCP tool definitions and handlers."""

from __future__ import annotations

import pytest

from armature.mcp.server import get_tool_definitions, handle_tool_call


class TestGetToolDefinitions:
    """Tests for MCP tool schema definitions."""

    def test_returns_list(self):
        tools = get_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_all_tools_have_name_and_schema(self):
        tools = get_tool_definitions()
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_expected_tools_present(self):
        tools = get_tool_definitions()
        names = {t["name"] for t in tools}
        expected = {
            "armature_check", "armature_heal", "armature_gc",
            "armature_budget", "armature_preplan", "armature_benchmark",
            "armature_estimate", "armature_baseline",
            "armature_pre_dev", "armature_post_dev",
            "armature_route", "armature_calibrate", "armature_cache_stats",
        }
        assert expected.issubset(names)


class TestHandleToolCall:
    """Tests for handle_tool_call() dispatcher."""

    def test_unknown_tool_returns_error(self):
        result = handle_tool_call("nonexistent_tool", {})
        assert "error" in result

    def test_check_tool_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = handle_tool_call("armature_check", {})
        assert "checks" in result or "score" in result

    def test_gc_tool_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = handle_tool_call("armature_gc", {})
        assert "findings" in result

    def test_pre_dev_tool_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = handle_tool_call("armature_pre_dev", {"env_check_only": True})
        assert "environment" in result
        assert "all_ok" in result

    def test_post_dev_tool_requires_baseline(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".armature" / "baselines").mkdir(parents=True, exist_ok=True)
        result = handle_tool_call("armature_post_dev", {"spec_id": "SPEC-001"})
        assert "error" in result  # no baseline exists yet

    def test_cache_stats_tool_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = handle_tool_call("armature_cache_stats", {})
        assert "entries" in result
