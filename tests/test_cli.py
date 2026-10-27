"""End-to-end CLI + renderer tests (no network, no browser)."""

from __future__ import annotations

import json

from gitpulse.cli import main
from gitpulse.metrics import analyze
from gitpulse.render import render_html


def test_cli_writes_html_and_json(sample_repo, tmp_path, capsys):
    out = tmp_path / "r.html"
    payload = tmp_path / "r.json"
    code = main([str(sample_repo), "--out", str(out), "--json", str(payload)])
    assert code == 0
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "demo-repo" in html
    assert "Commits per week" in html
    assert json.loads(payload.read_text())["totals"]["commits_analyzed"] == 5
    assert "gitpulse" in capsys.readouterr().out


def test_cli_rejects_non_repo(tmp_path, capsys):
    assert main([str(tmp_path), "--out", str(tmp_path / "x.html"), "-q"]) == 2
    assert "gitpulse:" in capsys.readouterr().err


def test_cli_handles_empty_repo(repo, tmp_path):
    out = tmp_path / "empty.html"
    assert main([str(repo), "--out", str(out), "-q"]) == 0
    assert "No activity in range." in out.read_text(encoding="utf-8")


def test_render_is_fully_self_contained(sample_repo):
    html = render_html(analyze(__import__("gitpulse").read_commits(sample_repo)))
    for forbidden in ("http://", "https://cdn", "<script"):
        assert forbidden not in html
    assert "<svg" in html  # charts are inline


def test_render_escapes_untrusted_commit_paths():
    from datetime import datetime, timezone

    from gitpulse.models import Commit, FileChange

    commit = Commit(
        sha="deadbeef",
        author_name="<script>alert(1)</script>",
        author_email="x@y.z",
        timestamp=datetime.now(timezone.utc),
        subject="feat: <img src=x onerror=alert(1)>",
        files=[FileChange("evil<script>.py", 1, 0)],
    )
    html = render_html(analyze([commit]))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
