"""Thin, defensive wrappers around the ``git`` binary.

Design notes
------------
* One subprocess call gets **everything** (headers + numstat) in a single pass —
  no per-commit queries, so a 50k-commit history still parses in one shot.
* Records are delimited with ASCII control characters (``\\x1e`` / ``\\x1f``)
  instead of newlines or pipes, which is what makes subjects containing
  newlines, tabs, ``|`` or even emoji safe to parse.
* ``encoding="utf-8", errors="replace"`` guarantees no crash on repos with
  legacy/latin-1 commit messages.
* ``--no-merges`` is deliberate: merge commits duplicate the same diff under a
  second SHA and would double-count churn in every metric.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime
from pathlib import Path

from .models import Commit, FileChange

RECORD = "\x1e"  # start-of-record
FIELD = "\x1f"  # field separator
NUMSTAT_RE = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")


class GitError(RuntimeError):
    """Raised when git is missing, the path is not a repo, or a command fails."""


def _run(repo: str | Path, args: list[str]) -> str:
    """Run a git command and return stdout, converting failures into GitError."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("The `git` executable was not found on your PATH.") from exc
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "git failed").strip().splitlines()
        raise GitError(message[-1] if message else f"git {' '.join(args)} failed")
    return proc.stdout


def ensure_repo(path: str | Path = ".") -> Path:
    """Validate that *path* is inside a git work tree and return its root."""
    root = _run(path, ["rev-parse", "--show-toplevel"]).strip()
    if not root:
        raise GitError(f"Not a git repository: {path}")
    return Path(root)


def repo_name(path: str | Path = ".") -> str:
    """Human-facing repo name: the directory name of the work tree root."""
    try:
        return ensure_repo(path).name
    except GitError:
        return Path(path).resolve().name


def current_branch(path: str | Path = ".") -> str:
    """Branch name, or the short SHA when HEAD is detached."""
    try:
        branch = _run(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
        return "detached" if branch in {"", "HEAD"} else branch
    except GitError:
        return "unknown"


def head_sha(path: str | Path = ".") -> str:
    try:
        return _run(path, ["rev-parse", "--short", "HEAD"]).strip()
    except GitError:
        return ""


def count_commits(path: str | Path = ".") -> int:
    """Total commits reachable from HEAD (merges included)."""
    try:
        out = _run(path, ["rev-list", "--count", "HEAD"]).strip()
        return int(out) if out.isdigit() else 0
    except GitError:
        return 0


def normalize_path(raw: str) -> str:
    """Collapse git's rename notation into the *new* path.

    Handles both ``old => new`` and the compact ``dir/{a => b}/file`` form.
    """
    raw = raw.strip()
    if "=>" not in raw:
        return raw
    if "{" in raw and "}" in raw:
        prefix, rest = raw.split("{", 1)
        inner, suffix = rest.split("}", 1)
        new_part = inner.split("=>", 1)[1]
        return f"{prefix}{new_part.strip()}{suffix}".replace("//", "/").strip()
    return raw.split("=>", 1)[1].strip()


def _parse(output: str) -> list[Commit]:
    """Turn raw ``git log`` output into :class:`Commit` objects."""
    commits: list[Commit] = []
    current: Commit | None = None

    # NOTE: never use str.splitlines() here — it treats \x1c-\x1e as line
    # boundaries, which would shred our record separators.
    for line in output.split("\n"):
        if line.startswith(RECORD):
            header = line[len(RECORD) :].split(FIELD)
            if len(header) < 5:
                current = None
                continue
            sha, name, email, iso_ts, subject = header[0], header[1], header[2], header[3], FIELD.join(header[4:])
            try:
                ts = datetime.fromisoformat(iso_ts.strip())
            except ValueError:
                current = None
                continue
            current = Commit(
                sha=sha.strip(),
                author_name=name.strip() or "unknown",
                author_email=email.strip(),
                timestamp=ts,
                subject=subject.strip(),
            )
            commits.append(current)
            continue

        if current is None or not line.strip():
            continue

        match = NUMSTAT_RE.match(line)
        if not match:
            continue
        added_raw, deleted_raw, path_raw = match.groups()
        binary = added_raw == "-" or deleted_raw == "-"
        current.files.append(
            FileChange(
                path=normalize_path(path_raw),
                added=0 if binary else int(added_raw),
                deleted=0 if binary else int(deleted_raw),
                binary=binary,
            )
        )

    return commits


def read_commits(
    path: str | Path = ".",
    *,
    since: str | None = None,
    author: str | None = None,
    limit: int | None = None,
) -> list[Commit]:
    """Read commits (newest first) with their per-file numstat in one pass."""
    args = [
        "log",
        f"--pretty=format:{RECORD}%H{FIELD}%an{FIELD}%ae{FIELD}%aI{FIELD}%s",
        "--numstat",
        "--no-merges",
        "--no-color",
    ]
    if since:
        args.append(f"--since={since}")
    if author:
        args.append(f"--author={author}")
    if limit:
        args.append(f"-n{int(limit)}")

    try:
        output = _run(path, args)
    except GitError as exc:
        # An empty repository has no HEAD: that is a valid, empty history.
        if "does not have any commits" in str(exc) or "unknown revision" in str(exc):
            return []
        raise
    return _parse(output)
