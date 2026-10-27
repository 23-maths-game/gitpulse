"""Immutable data containers used across gitpulse.

Everything downstream of :mod:`gitpulse.gitread` speaks in these types, which
keeps parsing concerns (subprocess, encodings, separators) fully isolated from
analysis and rendering concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class FileChange:
    """A single file touched by a commit, as reported by ``git log --numstat``."""

    path: str
    added: int
    deleted: int
    binary: bool = False

    @property
    def churn(self) -> int:
        """Lines added plus lines deleted (0 for binary files)."""
        return self.added + self.deleted


@dataclass(slots=True)
class Commit:
    """One non-merge commit plus the files it changed."""

    sha: str
    author_name: str
    author_email: str
    timestamp: datetime
    subject: str
    files: list[FileChange] = field(default_factory=list)

    @property
    def author_key(self) -> str:
        """Stable identity for an author: e-mail when present, else name."""
        return (self.author_email or self.author_name).strip().lower()

    @property
    def day(self) -> date:
        """Calendar day in the author's own UTC offset (not the runner's tz)."""
        return self.timestamp.date()


@dataclass(slots=True)
class AuthorStat:
    name: str
    email: str
    commits: int
    added: int
    deleted: int
    first_seen: datetime
    last_seen: datetime

    @property
    def churn(self) -> int:
        return self.added + self.deleted


@dataclass(slots=True)
class FileStat:
    path: str
    changes: int
    added: int
    deleted: int

    @property
    def churn(self) -> int:
        return self.added + self.deleted


@dataclass(slots=True)
class Analysis:
    """Full result of an analysis run. Pure data — no git handles, no paths."""

    repo_name: str
    branch: str
    head_sha: str
    total_commits_in_repo: int
    commits_analyzed: int
    first_commit: datetime | None
    last_commit: datetime | None
    added: int
    deleted: int
    authors: list[AuthorStat]
    files: list[FileStat]
    weekly: list[tuple[str, int]]
    weekday_hour: list[list[int]]
    active_days: int
    longest_streak: int
    streak_start: date | None
    streak_end: date | None
    commit_types: list[tuple[str, int]]
    short_subjects: int

    @property
    def bus_factor(self) -> int:
        """Fewest authors responsible for >50% of commits (a.k.a. lottery number)."""
        if self.commits_analyzed == 0:
            return 0
        half = self.commits_analyzed / 2
        running = 0
        for i, author in enumerate(self.authors, start=1):
            running += author.commits
            if running > half:
                return i
        return len(self.authors)

    @property
    def avg_commits_per_active_day(self) -> float:
        if not self.active_days:
            return 0.0
        return self.commits_analyzed / self.active_days

    def to_dict(self) -> dict:
        """JSON-safe projection of the report (used by ``--json``)."""

        def iso(value: datetime | date | None) -> str | None:
            return value.isoformat() if value is not None else None

        return {
            "repo": self.repo_name,
            "branch": self.branch,
            "head": self.head_sha,
            "totals": {
                "commits_in_repo": self.total_commits_in_repo,
                "commits_analyzed": self.commits_analyzed,
                "added": self.added,
                "deleted": self.deleted,
                "net": self.added - self.deleted,
                "active_days": self.active_days,
                "longest_streak_days": self.longest_streak,
                "bus_factor": self.bus_factor,
                "avg_commits_per_active_day": round(self.avg_commits_per_active_day, 2),
                "short_subjects": self.short_subjects,
            },
            "range": {
                "first_commit": iso(self.first_commit),
                "last_commit": iso(self.last_commit),
                "streak_start": iso(self.streak_start),
                "streak_end": iso(self.streak_end),
            },
            "authors": [
                {
                    "name": a.name,
                    "email": a.email,
                    "commits": a.commits,
                    "added": a.added,
                    "deleted": a.deleted,
                    "first_seen": iso(a.first_seen),
                    "last_seen": iso(a.last_seen),
                }
                for a in self.authors
            ],
            "files": [
                {"path": f.path, "changes": f.changes, "added": f.added, "deleted": f.deleted}
                for f in self.files
            ],
            "weekly": [{"week": w, "commits": c} for w, c in self.weekly],
            "commit_types": [{"type": t, "count": c} for t, c in self.commit_types],
        }
