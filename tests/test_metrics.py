"""Tests for the pure aggregation layer."""

from __future__ import annotations

from datetime import date, datetime, timezone

from gitpulse import gitread
from gitpulse.metrics import analyze, extension_breakdown, longest_streak
from gitpulse.models import Commit, FileChange


def _commit(day: int, subject: str = "feat: x", email: str = "a@x.com", hour: int = 10) -> Commit:
    return Commit(
        sha=f"{day:04d}",
        author_name=email.split("@")[0],
        author_email=email,
        timestamp=datetime(2024, 3, day, hour, tzinfo=timezone.utc),
        subject=subject,
        files=[FileChange("f.py", 10, 1)],
    )


def test_empty_history_is_valid():
    a = analyze([])
    assert a.commits_analyzed == 0
    assert a.bus_factor == 0
    assert a.authors == []
    assert a.weekly == []
    assert a.to_dict()["totals"]["net"] == 0


def test_totals_and_authors(sample_repo):
    a = analyze(gitread.read_commits(sample_repo), repo_name="demo-repo")
    assert a.commits_analyzed == 5
    assert [x.name for x in a.authors] == ["Alice", "Bob", "Carol"]
    assert a.authors[0].commits == 3
    assert a.added == 97 and a.deleted == 3
    assert a.active_days == 4
    # Alice alone owns 3/5 = 60% of commits.
    assert a.bus_factor == 1


def test_hotspot_ordering(sample_repo):
    a = analyze(gitread.read_commits(sample_repo))
    assert a.files[0].path == "app/core.py"
    assert a.files[0].changes == 3
    assert a.files[0].added == 27
    assert a.files[0].deleted == 3


def test_bus_factor_counts_authors_needed_to_exceed_half():
    # 4 commits, 2 each -> nobody alone owns >50%, so both are required.
    even = [
        _commit(1, email="a@x.com"),
        _commit(2, email="a@x.com"),
        _commit(3, email="b@x.com"),
        _commit(4, email="b@x.com"),
    ]
    assert analyze(even).bus_factor == 2
    # 2 of 3 commits (66%) puts the whole project in one person's head.
    skewed = [_commit(1, email="a@x.com"), _commit(2, email="a@x.com"), _commit(3, email="b@x.com")]
    assert analyze(skewed).bus_factor == 1


def test_weekly_series_is_dense_and_monday_anchored():
    # 2024-03-04 is a Monday; 2024-03-20 is two weeks later.
    commits = [_commit(4), _commit(6), _commit(20)]
    weekly = analyze(commits).weekly
    assert weekly[0][0] == "2024-03-04"
    assert [c for _, c in weekly] == [2, 0, 1]


def test_heatmap_bucket_placement():
    a = analyze([_commit(4, hour=13)])
    # 2024-03-04 is a Monday -> row 0; hour 13 -> column 13.
    assert a.weekday_hour[0][13] == 1
    assert sum(sum(row) for row in a.weekday_hour) == 1


def test_longest_streak():
    days = {date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 9)}
    length, start, end = longest_streak(days)
    assert (length, start, end) == (3, date(2024, 1, 1), date(2024, 1, 3))
    assert longest_streak(set()) == (0, None, None)


def test_conventional_commit_detection():
    a = analyze([_commit(1, "feat(api)!: breaking"), _commit(2, "update stuff"), _commit(3, "fix: bug")])
    assert dict(a.commit_types) == {"feat": 1, "fix": 1}
    assert a.short_subjects >= 1  # "fix: bug" is short


def test_extension_breakdown():
    commits = [
        Commit("a", "x", "x@y", datetime.now(timezone.utc), "x", [FileChange("a.py", 1, 0)]),
        Commit("b", "x", "x@y", datetime.now(timezone.utc), "y", [FileChange("b.py", 1, 0)]),
        Commit("c", "x", "x@y", datetime.now(timezone.utc), "z", [FileChange("Makefile", 1, 0)]),
    ]
    a = analyze(commits)
    assert extension_breakdown(a.files)[0] == (".py", 2)


def test_to_dict_is_json_safe(sample_repo):
    import json

    payload = json.dumps(analyze(gitread.read_commits(sample_repo)).to_dict())
    assert '"bus_factor": 1' in payload
