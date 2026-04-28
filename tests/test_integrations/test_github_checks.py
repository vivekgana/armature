"""Tests for integrations/github_checks.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from armature._internal.types import CheckResult
from armature.integrations.github_checks import (
    _Annotation,
    build_annotations_from_ruff_output,
    post_check_run,
)


@pytest.fixture()
def passing_results() -> list[CheckResult]:
    return [
        CheckResult(name="lint", passed=True, score=1.0, weight=25),
        CheckResult(name="type_check", passed=True, score=1.0, weight=25),
    ]


@pytest.fixture()
def failing_results() -> list[CheckResult]:
    return [
        CheckResult(name="lint", passed=False, violation_count=5, score=0.7, weight=25, details="ruff: 5 violations"),
        CheckResult(name="type_check", passed=True, score=1.0, weight=25),
    ]


class TestPostCheckRun:
    def test_skips_when_env_vars_missing(self, passing_results):
        """Should return False and not make any HTTP calls when env vars are absent."""
        with patch.dict("os.environ", {}, clear=True), patch("urllib.request.urlopen") as mock_open:
            result = post_check_run(passing_results)
        assert result is False
        mock_open.assert_not_called()

    def test_calls_github_api_when_env_set(self, passing_results):
        env = {
            "GITHUB_TOKEN": "tok_test",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123",
        }
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.status = 201

        with patch.dict("os.environ", env), patch("urllib.request.urlopen", return_value=mock_response):
            result = post_check_run(passing_results)

        assert result is True

    def test_success_conclusion_when_all_pass(self, passing_results):
        env = {
            "GITHUB_TOKEN": "tok",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "sha1",
        }
        captured_payload: dict = {}

        def fake_urlopen(req, timeout=None):
            captured_payload.update(json.loads(req.data.decode()))
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.status = 201
            return resp

        with patch.dict("os.environ", env), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            post_check_run(passing_results)

        assert captured_payload["conclusion"] == "success"

    def test_failure_conclusion_when_some_fail(self, failing_results):
        env = {
            "GITHUB_TOKEN": "tok",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "sha1",
        }
        captured_payload: dict = {}

        def fake_urlopen(req, timeout=None):
            captured_payload.update(json.loads(req.data.decode()))
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.status = 201
            return resp

        with patch.dict("os.environ", env), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            post_check_run(failing_results)

        assert captured_payload["conclusion"] == "failure"

    def test_returns_false_on_http_error(self, passing_results):
        import urllib.error
        env = {
            "GITHUB_TOKEN": "tok",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "sha1",
        }
        with patch.dict("os.environ", env), patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None,  # type: ignore[arg-type]
        )):
            result = post_check_run(passing_results)
        assert result is False

    def test_returns_false_on_network_error(self, passing_results):
        import urllib.error
        env = {
            "GITHUB_TOKEN": "tok",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "sha1",
        }
        with (
            patch.dict("os.environ", env),
            patch("urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")),
        ):
            result = post_check_run(passing_results)
        assert result is False

    def test_annotations_included_in_payload(self, passing_results):
        env = {
            "GITHUB_TOKEN": "tok",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "sha1",
        }
        captured_payload: dict = {}

        def fake_urlopen(req, timeout=None):
            captured_payload.update(json.loads(req.data.decode()))
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.status = 201
            return resp

        ann = _Annotation(
            path="src/foo.py", start_line=10, end_line=10,
            annotation_level="warning", message="E501 line too long", title="ruff: E501",
        )
        with patch.dict("os.environ", env), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            post_check_run(passing_results, annotations=[ann])

        output_annotations = captured_payload["output"]["annotations"]
        assert len(output_annotations) == 1
        assert output_annotations[0]["path"] == "src/foo.py"


class TestBuildAnnotationsFromRuffOutput:
    def test_parses_valid_json(self):
        ruff_json = json.dumps([
            {
                "filename": "src/foo.py",
                "location": {"row": 10, "column": 1},
                "code": "E501",
                "message": "Line too long",
                "url": "https://docs.astral.sh/ruff/rules/E501",
            }
        ])
        anns = build_annotations_from_ruff_output(ruff_json)
        assert len(anns) == 1
        assert anns[0].path == "src/foo.py"
        assert anns[0].start_line == 10
        assert "E501" in anns[0].title

    def test_empty_string_returns_empty(self):
        assert build_annotations_from_ruff_output("") == []

    def test_invalid_json_returns_empty(self):
        assert build_annotations_from_ruff_output("{not valid json}") == []

    def test_caps_at_50_annotations(self):
        items = [
            {"filename": "f.py", "location": {"row": i, "column": 0},
             "code": "E501", "message": "msg"}
            for i in range(100)
        ]
        anns = build_annotations_from_ruff_output(json.dumps(items))
        assert len(anns) == 50
