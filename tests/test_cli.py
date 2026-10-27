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


# --------------------------------------------------------------------------- #
# --compare-to : window vs preceding window of equal length
# --------------------------------------------------------------------------- #
def test_compare_to_adds_comparison_to_json_and_html(bot_repo, tmp_path):
    out, payload = tmp_path / "c.html", tmp_path / "c.json"
    code = main([str(bot_repo), "--compare-to", "2024-05-02", "--out", str(out), "--json", str(payload), "-q"])
    assert code == 0

    data = json.loads(payload.read_text())
    assert "comparison" in data
    rows = {row["metric"]: row for row in data["comparison"]}
    assert {"Commits", "Contributors", "Bus factor"} <= set(rows)
    assert rows["Commits"]["current"] == 2          # two human commits on 2024-05-02
    assert rows["Commits"]["baseline"] == 1         # one human commit in the prior window
    assert rows["Commits"]["change"] == 1

    html = out.read_text(encoding="utf-8")
    assert "Period comparison" in html
    assert "improved" in html and "regressed" in html


def test_compare_to_handles_empty_baseline(bot_repo, tmp_path):
    """A repo whose whole history sits inside the current window must not crash."""
    out = tmp_path / "empty-base.html"
    assert main([str(bot_repo), "--compare-to", "2000-01-01", "--out", str(out), "-q"]) == 0
    assert "Period comparison" in out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Bot filtering
# --------------------------------------------------------------------------- #
def test_bots_excluded_by_default_with_a_note(bot_repo, tmp_path):
    out, payload = tmp_path / "bots.html", tmp_path / "bots.json"
    main([str(bot_repo), "--out", str(out), "--json", str(payload), "-q"])
    data = json.loads(payload.read_text())
    assert data["totals"]["commits_analyzed"] == 3
    assert data["notes"] == ["2 bot commits excluded"]
    assert [a["name"] for a in data["authors"]] == ["Dev One", "Dev Two"]
    assert "bot commits excluded" in out.read_text(encoding="utf-8")


def test_include_bots_keeps_automation(bot_repo, tmp_path):
    payload = tmp_path / "with-bots.json"
    main([str(bot_repo), "--include-bots", "--out", str(tmp_path / "b.html"),
          "--json", str(payload), "-q"])
    data = json.loads(payload.read_text())
    assert data["totals"]["commits_analyzed"] == 5
    assert data["notes"] == []
    assert any("dependabot" in a["name"] for a in data["authors"])
