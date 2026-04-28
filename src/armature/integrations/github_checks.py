"""Post Armature check results as GitHub Checks API annotations.

This integration posts inline PR annotations (file + line) for each quality
violation when running inside a GitHub Actions environment.  It requires the
``GITHUB_TOKEN`` secret and runs automatically when the required env vars
(``GITHUB_REPOSITORY``, ``GITHUB_SHA``, ``GITHUB_TOKEN``) are present.

Usage (called from the generated armature.yml workflow or action.yml)::

    from armature.integrations.github_checks import post_check_run
    post_check_run(results, title="Armature Quality Gates")
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from armature._internal.types import CheckResult

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


@dataclass
class _Annotation:
    path: str
    start_line: int
    end_line: int
    annotation_level: str  # "notice" | "warning" | "failure"
    message: str
    title: str


def post_check_run(
    results: list[CheckResult],
    *,
    title: str = "Armature Quality Gates",
    annotations: list[_Annotation] | None = None,
) -> bool:
    """Create or update a GitHub Check Run with Armature quality results.

    Returns ``True`` on success, ``False`` if the environment variables are
    missing or the API call fails (so CI doesn't break on network errors).

    Args:
        results: Quality check results from :func:`~armature.quality.scorer.run_quality_checks`.
        title: Check run name shown in the GitHub PR Checks tab.
        annotations: Optional list of file-level annotations to attach.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")

    if not (token and repo and sha):
        logger.debug(
            "GitHub Checks integration skipped: GITHUB_TOKEN / GITHUB_REPOSITORY / GITHUB_SHA not set"
        )
        return False

    passed = all(r.passed for r in results)
    total_weight = sum(r.weight for r in results)
    weighted_score = sum(r.score * r.weight for r in results) / total_weight if total_weight else 1.0

    conclusion = "success" if passed else "failure"
    gate = "merge_ready" if weighted_score >= 0.95 else "review_ready" if weighted_score >= 0.85 else "draft"

    summary_rows = "\n".join(
        f"| {r.name} | {'✅' if r.passed else '❌'} | {r.score:.2f} | {r.weight} | {r.details} |"
        for r in results
    )
    summary = (
        f"**Quality score:** `{weighted_score:.2f}` — gate: `{gate}`\n\n"
        "| Check | Status | Score | Weight | Details |\n"
        "|-------|--------|-------|--------|---------|\n"
        f"{summary_rows}\n"
    )

    payload: dict[str, object] = {
        "name": title,
        "head_sha": sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": f"Armature: {gate.replace('_', ' ').title()} ({weighted_score:.0%})",
            "summary": summary,
            "annotations": [
                {
                    "path": a.path,
                    "start_line": a.start_line,
                    "end_line": a.end_line,
                    "annotation_level": a.annotation_level,
                    "message": a.message,
                    "title": a.title,
                }
                for a in (annotations or [])
            ][:50],  # GitHub API limit: 50 annotations per request
        },
    }

    url = f"{_GITHUB_API}/repos/{repo}/check-runs"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            logger.debug("GitHub Checks API response: %s", status)
            return status in (200, 201)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning("GitHub Checks API HTTP error %s: %s", exc.code, body)
        return False
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("GitHub Checks API request failed: %s", exc)
        return False


def build_annotations_from_ruff_output(ruff_output: str) -> list[_Annotation]:
    """Parse ``ruff check --output-format json`` output into Checks API annotations.

    Args:
        ruff_output: Raw JSON string from ``ruff check --output-format json``.

    Returns:
        List of :class:`_Annotation` objects ready to pass to :func:`post_check_run`.
    """
    annotations: list[_Annotation] = []
    try:
        data = json.loads(ruff_output) if ruff_output.strip() else []
    except json.JSONDecodeError:
        return annotations

    for item in data:
        if not isinstance(item, dict):
            continue
        location = item.get("location", {})
        path = item.get("filename", "")
        line = location.get("row", 1)
        code = item.get("code", "")
        message = item.get("message", "")
        url = item.get("url", "")
        full_message = f"[{code}] {message}"
        if url:
            full_message += f"\nSee: {url}"
        annotations.append(
            _Annotation(
                path=path,
                start_line=max(1, line),
                end_line=max(1, line),
                annotation_level="warning",
                message=full_message,
                title=f"ruff: {code}",
            )
        )
    return annotations[:50]  # cap at GitHub API limit
