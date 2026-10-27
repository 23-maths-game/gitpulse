"""Shared pytest fixtures: throwaway git repositories built deterministically."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    full_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        **(env or {}),
    }
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=full_env,
    )
    return proc.stdout


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """An empty repo with a `main` branch and no commits."""
    path = tmp_path / "demo-repo"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    return path


@pytest.fixture()
def sample_repo(repo: Path) -> Path:
    """A repo with 5 commits across 3 authors and 3 files.

    Diffs are constructed exactly so numstat is predictable:
        +20 -0  app/core.py   feat: add engine          (2024-03-04, Alice)
        +5  -2  app/core.py   fix: handle empty input    (2024-03-04, Alice)
        +40 -0  README.md     docs: write readme         (2024-03-05, Bob)
        +30 -0  tests/t.py    test: cover engine         (2024-03-06, Carol)
        +2  -1  app/core.py   chore: tidy imports        (2024-03-07, Alice)
    Totals: 97 added / 3 deleted; app/core.py touched 3× (+27 -3).
    """
    core = [f"line {i}" for i in range(1, 21)]  # 20 lines

    def commit(date: str, who: str, subject: str, files: dict[str, list[str]]) -> None:
        name, email = who[:-1].split(" <")
        for rel, lines in files.items():
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(
            repo,
            "-c", f"user.name={name}",
            "-c", f"user.email={email}",
            "commit", "-q", "-m", subject,
            env={
                "GIT_AUTHOR_NAME": name,
                "GIT_AUTHOR_EMAIL": email,
                "GIT_AUTHOR_DATE": f"{date}T10:00:00+0000",
                "GIT_COMMITTER_NAME": name,
                "GIT_COMMITTER_EMAIL": email,
                "GIT_COMMITTER_DATE": f"{date}T10:00:00+0000",
            },
        )

    alice, bob, carol = "Alice <alice@example.com>", "Bob <bob@example.com>", "Carol <carol@example.com>"

    commit("2024-03-04", alice, "feat: add engine", {"app/core.py": core})
    # Drop 2 tail lines, add 5 new ones -> +5 -2
    commit(
        "2024-03-04", alice, "fix: handle empty input",
        {"app/core.py": core[:18] + [f"extra {i}" for i in range(1, 6)]},
    )
    commit("2024-03-05", bob, "docs: write readme", {"README.md": [f"doc {i}" for i in range(40)]})
    commit("2024-03-06", carol, "test: cover engine", {"tests/t.py": [f"assert {i}" for i in range(30)]})
    # Drop 1 line, add 2 -> +2 -1
    updated = core[:18] + [f"extra {i}" for i in range(1, 6)]
    commit(
        "2024-03-07", alice, "chore: tidy imports",
        {"app/core.py": updated[:-1] + ["tail a", "tail b"]},
    )
    return repo
