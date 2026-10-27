"""Tests for the git-parsing layer."""

from __future__ import annotations

import pytest

from gitpulse import gitread


def test_parse_reads_all_commits(sample_repo):
    commits = gitread.read_commits(sample_repo)
    assert len(commits) == 5
    # Newest first.
    assert commits[0].subject == "chore: tidy imports"
    assert all(c.sha for c in commits)
    assert all(c.timestamp.tzinfo is not None for c in commits)


def test_parse_attaches_numstat_to_the_right_commit(sample_repo):
    commits = {c.subject: c for c in gitread.read_commits(sample_repo)}
    feat = commits["feat: add engine"]
    assert len(feat.files) == 1
    assert feat.files[0].path == "app/core.py"
    assert feat.files[0].added == 20
    assert feat.files[0].deleted == 0

    fix = commits["fix: handle empty input"]
    assert fix.files[0].added == 5
    assert fix.files[0].deleted == 2


def test_read_commits_respects_limit_and_author(sample_repo):
    assert len(gitread.read_commits(sample_repo, limit=2)) == 2
    alice = gitread.read_commits(sample_repo, author="alice@example.com")
    assert len(alice) == 3
    assert {c.author_name for c in alice} == {"Alice"}


def test_read_commits_since_filters(sample_repo):
    recent = gitread.read_commits(sample_repo, since="2024-03-06T00:00:00")
    assert [c.subject for c in recent] == ["chore: tidy imports", "test: cover engine"]


def test_empty_repo_returns_no_commits(repo):
    assert gitread.read_commits(repo) == []


def test_ensure_repo_rejects_non_repo(tmp_path):
    with pytest.raises(gitread.GitError):
        gitread.ensure_repo(tmp_path)


def test_repo_metadata(sample_repo):
    assert gitread.ensure_repo(sample_repo).name == "demo-repo"
    assert gitread.current_branch(sample_repo) == "main"
    assert gitread.count_commits(sample_repo) == 5
    assert len(gitread.head_sha(sample_repo)) >= 7


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("app/core.py", "app/core.py"),
        ("old.py => new.py", "new.py"),
        ("src/{old => new}/mod.py", "src/new/mod.py"),
        ("pkg/{ => sub}/f.py", "pkg/sub/f.py"),
    ],
)
def test_normalize_path(raw, expected):
    assert gitread.normalize_path(raw) == expected


def test_survives_hostile_commit_subject(sample_repo):
    """Subjects containing the record separator's neighbours must not break parsing."""
    hostile = "weird \u00b7 subject | with pipe and \u00e9moji \U0001f680"
    (sample_repo / "x.txt").write_text("hi\n", encoding="utf-8")
    gitread.subprocess.run(
        ["git", "-C", str(sample_repo), "add", "-A"], check=True, capture_output=True
    )
    gitread.subprocess.run(
        [
            "git", "-C", str(sample_repo),
            "-c", "user.name=Hostile", "-c", "user.email=hostile@example.com",
            "commit", "-q", "-m", hostile,
        ],
        check=True,
        capture_output=True,
    )
    commits = gitread.read_commits(sample_repo)
    assert commits[0].subject == hostile
