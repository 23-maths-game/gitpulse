#!/usr/bin/env python3
"""Generate a throwaway repo with ~300 commits so the report has something to say.

Usage:
    python scripts/make_demo_repo.py /tmp/gitpulse-demo      # build the history
    gitpulse /tmp/gitpulse-demo -o docs/demo-report.html     # render the report

The history is deterministic (fixed seed, fixed dates) so the committed demo
report is reproducible byte-for-byte on any machine and any git version.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

AUTHORS = [
    ("Ada Lovelace", "ada@example.com"),
    ("Grace Hopper", "grace@example.com"),
    ("Linus T", "linus@example.com"),
    ("Katherine J", "katherine@example.com"),
]
TYPES = ["feat", "fix", "docs", "refactor", "test", "chore", "perf", "ci"]
SCOPES = ["api", "core", "ui", "db", "cli", ""]
FILES = [
    "src/api/routes.py",
    "src/core/engine.py",
    "src/core/parser.py",
    "src/ui/dashboard.js",
    "src/ui/chart.js",
    "src/db/schema.sql",
    "src/db/migrate.py",
    "tests/test_engine.py",
    "docs/guide.md",
    "README.md",
]


def git(repo: Path, *args: str, when: datetime, author: tuple[str, str]) -> None:
    env = {
        "GIT_AUTHOR_NAME": author[0],
        "GIT_AUTHOR_EMAIL": author[1],
        "GIT_COMMITTER_NAME": author[0],
        "GIT_COMMITTER_EMAIL": author[1],
        "GIT_AUTHOR_DATE": when.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        "GIT_COMMITTER_DATE": when.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(repo),
    }
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def main(target: str = "/tmp/gitpulse-demo") -> int:
    repo = Path(target)
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)

    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    rng = random.Random(20240301)  # fixed seed => reproducible demo

    start = datetime(2024, 9, 2, 9, 0)  # a Monday
    author = AUTHORS[0]
    commits = 0

    for day_offset in range(210):
        day = start + timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5
        if is_weekend and rng.random() > 0.28:
            continue
        # Effort ramps up over time, with a quiet dip mid-project.
        load = rng.randint(0, 3) + (2 if day_offset > 60 else 0)
        if 100 <= day_offset <= 118:
            load = max(0, load - 2)
        for _ in range(load):
            # Working hours, skewed late for the night owls.
            hour = rng.choice([9, 10, 10, 11, 11, 12, 14, 14, 15, 16, 17, 21, 22, 23])
            when = day.replace(hour=hour, minute=rng.randint(0, 59))
            author = rng.choices(AUTHORS, weights=[5, 3, 4, 2])[0]

            ctype = rng.choices(TYPES, weights=[30, 26, 8, 14, 10, 6, 4, 2])[0]
            scope = rng.choice(SCOPES)
            subject = f"{ctype}{f'({scope})' if scope else ''}: " + rng.choice(
                [
                    "wire up retry backoff",
                    "guard against empty payload",
                    "tighten input validation",
                    "cache parsed manifests",
                    "document the plugin hooks",
                    "split renderer from engine",
                    "drop deprecated helper",
                    "add regression coverage",
                    "harden csv import path",
                    "speed up hot loop",
                    "update build matrix",
                ]
            )
            # A few deliberately sloppy subjects so the message-quality metric fires.
            if rng.random() < 0.07:
                subject = rng.choice(["wip", "fix", "asdf", "minor", "oops"])

            for _ in range(rng.randint(1, 3)):
                rel = rng.choices(FILES, weights=[16, 18, 12, 10, 6, 6, 5, 12, 5, 4])[0]
                path = repo / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                kind = rng.random()
                existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
                if kind < 0.55:
                    # Grow the file.
                    existing += [f"# change {commits} {rng.random():.6f}" for _ in range(rng.randint(1, 12))]
                elif kind < 0.8:
                    # Rewrite a slice: real deletions, not just appends.
                    existing += [f"# tweak {commits}" for _ in range(rng.randint(1, 4))]
                    if existing:
                        del existing[rng.randrange(len(existing)) :][: rng.randint(1, 6)]
                elif existing:
                    # Refactor pass: drop a chunk of stale lines.
                    cut = rng.randint(1, max(1, min(8, len(existing))))
                    del existing[:cut]
                else:
                    existing = [f"# bootstrap {commits}"]
                path.write_text("\n".join(existing) + "\n", encoding="utf-8")

            git(repo, "add", "-A", when=when, author=author)
            git(repo, "commit", "-q", "-m", subject, when=when, author=author)
            commits += 1

    print(f"built {repo} with {commits} commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
