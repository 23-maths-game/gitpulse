"""Pure aggregation: ``list[Commit]`` in, one :class:`Analysis` out.

No I/O happens here, which is what makes the whole module trivially testable.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import PurePosixPath

from .models import Analysis, AuthorStat, Commit, FileStat

CONVENTIONAL_TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
SHORT_SUBJECT_LIMIT = 15  # characters; below this a subject is near-useless
MAX_WEEKS = 30  # chart window, keeps the SVG readable
MAX_FILES = 25  # rows in the hotspot table


def _week_start(day: date) -> date:
    """Monday of the ISO week containing *day*."""
    return day - timedelta(days=day.weekday())


def longest_streak(days: set[date]) -> tuple[int, date | None, date | None]:
    """Return ``(length, start, end)`` of the longest run of consecutive days."""
    best_len, best_start, best_end = 0, None, None
    run_len, run_start, prev = 0, None, None
    for day in sorted(days):
        if prev is not None and (day - prev).days == 1:
            run_len += 1
        else:
            run_len, run_start = 1, day
        if run_len > best_len:
            best_len, best_start, best_end = run_len, run_start, day
        prev = day
    return best_len, best_start, best_end


def _commit_type(subject: str) -> str | None:
    """Extract a Conventional Commits type (``feat(api): ...`` -> ``feat``)."""
    head = subject.split(":", 1)[0].strip().lower()
    head = head.split("(", 1)[0].split("!", 1)[0].strip()
    return head if head in CONVENTIONAL_TYPES else None


def analyze(
    commits: list[Commit],
    *,
    repo_name: str = "repository",
    branch: str = "main",
    head_sha: str = "",
    total_commits_in_repo: int | None = None,
) -> Analysis:
    """Aggregate raw commits into a fully rendered-ready report model."""
    if not commits:
        return Analysis(
            repo_name=repo_name,
            branch=branch,
            head_sha=head_sha,
            total_commits_in_repo=total_commits_in_repo or 0,
            commits_analyzed=0,
            first_commit=None,
            last_commit=None,
            added=0,
            deleted=0,
            authors=[],
            files=[],
            weekly=[],
            weekday_hour=[[0] * 24 for _ in range(7)],
            active_days=0,
            longest_streak=0,
            streak_start=None,
            streak_end=None,
            commit_types=[],
            short_subjects=0,
        )

    author_acc: dict[str, dict] = {}
    file_changes: Counter[str] = Counter()
    file_added: Counter[str] = Counter()
    file_deleted: Counter[str] = Counter()
    per_day: Counter[date] = Counter()
    weekday_hour = [[0] * 24 for _ in range(7)]
    types: Counter[str] = Counter()
    added = deleted = short_subjects = 0

    for commit in commits:
        # --- author rollup -------------------------------------------------
        acc = author_acc.get(commit.author_key)
        if acc is None:
            acc = author_acc[commit.author_key] = {
                "name": commit.author_name,
                "email": commit.author_email,
                "commits": 0,
                "added": 0,
                "deleted": 0,
                "first": commit.timestamp,
                "last": commit.timestamp,
            }
        acc["commits"] += 1
        acc["last"] = max(acc["last"], commit.timestamp)
        acc["first"] = min(acc["first"], commit.timestamp)
        if len(commit.author_name) > len(acc["name"]):
            acc["name"] = commit.author_name  # prefer the least abbreviated name

        # --- temporal rollup ----------------------------------------------
        per_day[commit.day] += 1
        weekday_hour[commit.timestamp.weekday()][commit.timestamp.hour] += 1

        # --- message quality ----------------------------------------------
        if len(commit.subject.strip()) < SHORT_SUBJECT_LIMIT:
            short_subjects += 1
        ctype = _commit_type(commit.subject)
        if ctype:
            types[ctype] += 1

        # --- file rollup ---------------------------------------------------
        for change in commit.files:
            added += change.added
            deleted += change.deleted
            acc["added"] += change.added
            acc["deleted"] += change.deleted
            file_changes[change.path] += 1
            file_added[change.path] += change.added
            file_deleted[change.path] += change.deleted

    authors = sorted(
        (
            AuthorStat(
                name=v["name"],
                email=v["email"],
                commits=v["commits"],
                added=v["added"],
                deleted=v["deleted"],
                first_seen=v["first"],
                last_seen=v["last"],
            )
            for v in author_acc.values()
        ),
        key=lambda a: (-a.commits, a.name.lower()),
    )

    files = sorted(
        (
            FileStat(path=p, changes=c, added=file_added[p], deleted=file_deleted[p])
            for p, c in file_changes.items()
        ),
        key=lambda f: (-f.changes, -f.churn, f.path.lower()),
    )[:MAX_FILES]

    # --- weekly series (dense, zero-filled, Monday-anchored) ----------------
    first_day = min(per_day)
    last_day = max(per_day)
    start_week = _week_start(first_day)
    end_week = _week_start(last_day)
    week_counts: dict[date, int] = defaultdict(int)
    for day, count in per_day.items():
        week_counts[_week_start(day)] += count

    total_weeks = ((end_week - start_week).days // 7) + 1
    if total_weeks > MAX_WEEKS:  # keep the newest window, still zero-filled
        start_week = end_week - timedelta(weeks=MAX_WEEKS - 1)
    weekly = []
    cursor = start_week
    while cursor <= end_week:
        weekly.append((cursor.isoformat(), week_counts.get(cursor, 0)))
        cursor += timedelta(weeks=1)

    streak_len, streak_start, streak_end = longest_streak(set(per_day))

    return Analysis(
        repo_name=repo_name,
        branch=branch,
        head_sha=head_sha,
        total_commits_in_repo=total_commits_in_repo or len(commits),
        commits_analyzed=len(commits),
        first_commit=min(c.timestamp for c in commits),
        last_commit=max(c.timestamp for c in commits),
        added=added,
        deleted=deleted,
        authors=authors,
        files=files,
        weekly=weekly,
        weekday_hour=weekday_hour,
        active_days=len(per_day),
        longest_streak=streak_len,
        streak_start=streak_start,
        streak_end=streak_end,
        commit_types=sorted(types.items(), key=lambda kv: (-kv[1], kv[0])),
        short_subjects=short_subjects,
    )


def extension_breakdown(files: list[FileStat]) -> list[tuple[str, int]]:
    """Commit-touch counts grouped by file extension (``<none>`` for dotfiles)."""
    bucket: Counter[str] = Counter()
    for f in files:
        suffix = PurePosixPath(f.path).suffix.lower()
        bucket[suffix or "<none>"] += f.changes
    return sorted(bucket.items(), key=lambda kv: (-kv[1], kv[0]))


# --------------------------------------------------------------------------- #
# Bot / automation filtering
# --------------------------------------------------------------------------- #
# Commit bots distort every author-facing metric: dependabot alone can out-commit
# the entire team and quietly push the bus factor to a meaningless "1".
BOT_RE = re.compile(
    r"""(?xi)
    \[bot\]                          # GitHub Apps: "dependabot[bot]"
    | ^(?:dependabot|renovate|github-actions|pre-commit-ci|snyk-bot|
          greenkeeper|mergify|allcontributors|semantic-release-bot|
          pyup-bot|imgbot|restyled|codecov|sonarcloud|copilot|claude|codex)[-\w]*
    | (?:^|[-_.@])(?:bot|ci|automation|crawler)(?:$|[-_.@\d])
    | @(?:users\.noreply\.github\.com$)
    """,
)


def is_bot(commit: Commit) -> bool:
    """True when a commit was authored by automation rather than a human."""
    return bool(BOT_RE.search(commit.author_name.strip()) or BOT_RE.search(commit.author_email.strip()))


def filter_bots(commits: list[Commit]) -> tuple[list[Commit], int]:
    """Split commits into ``(humans, dropped_bot_commits)``."""
    humans = [c for c in commits if not is_bot(c)]
    return humans, len(commits) - len(humans)


# --------------------------------------------------------------------------- #
# Period-over-period comparison
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class Delta:
    """One row of the period-comparison table."""

    label: str
    baseline: float
    current: float
    unit: str = ""
    higher_is_better: bool | None = None  # None = neutral metric, no colour

    @property
    def change(self) -> float:
        return self.current - self.baseline

    @property
    def pct(self) -> float | None:
        """Relative change, or ``None`` when the baseline is zero (undefined)."""
        return None if self.baseline == 0 else (self.change / self.baseline) * 100.0

    @property
    def sentiment(self) -> str:
        """``better`` / ``worse`` / ``flat`` — drives the colour in the report."""
        if self.change == 0 or self.higher_is_better is None:
            return "flat"
        good = self.change > 0 if self.higher_is_better else self.change < 0
        return "better" if good else "worse"


def compare(current: Analysis, baseline: Analysis) -> list[Delta]:
    """Build the delta rows for ``current`` measured against ``baseline``."""

    def per_day(a: Analysis) -> float:
        return round(a.avg_commits_per_active_day, 2)

    return [
        Delta("Commits", baseline.commits_analyzed, current.commits_analyzed, higher_is_better=True),
        Delta("Contributors", len(baseline.authors), len(current.authors), higher_is_better=None),
        Delta("Lines added", baseline.added, current.added, higher_is_better=None),
        Delta("Lines deleted", baseline.deleted, current.deleted, higher_is_better=None),
        Delta("Net lines", baseline.added - baseline.deleted, current.added - current.deleted,
              higher_is_better=True),
        Delta("Active days", baseline.active_days, current.active_days, higher_is_better=True),
        Delta("Commits / active day", per_day(baseline), per_day(current), higher_is_better=True),
        Delta("Bus factor", baseline.bus_factor, current.bus_factor, higher_is_better=False),
        Delta("Longest streak", baseline.longest_streak, current.longest_streak,
              unit="d", higher_is_better=True),
    ]
