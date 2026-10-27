"""Command-line interface: ``gitpulse [PATH] [options]``."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__, gitread
from .metrics import analyze, compare, filter_bots
from .render import render_html


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gitpulse",
        description="Zero-dependency git repository intelligence — one self-contained HTML report.",
        epilog="Examples:\n"
        "  gitpulse                      # analyse the current repo\n"
        "  gitpulse ~/code/api --since '6 months ago'\n"
        "  gitpulse . --compare-to '3 months ago'   # this quarter vs last quarter\n"
        "  gitpulse . --json stats.json --out report.html",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", nargs="?", default=".", help="path inside a git repo (default: .)")
    p.add_argument("-o", "--out", default="gitpulse-report.html", help="HTML output path")
    p.add_argument("--json", metavar="FILE", help="also write the raw metrics as JSON")
    p.add_argument("--since", metavar="DATE", help="limit history, e.g. '2024-01-01' or '6 months ago'")
    p.add_argument("--author", metavar="PATTERN", help="only commits by this author (regex as git accepts it)")
    p.add_argument("--limit", type=int, metavar="N", help="analyse at most N commits")
    p.add_argument(
        "--compare-to",
        metavar="DATE",
        help="compare the window since DATE against the preceding window of equal length "
        "(e.g. '3 months ago' = this quarter vs last quarter)",
    )
    p.add_argument(
        "--include-bots",
        action="store_true",
        help="count automation accounts (dependabot[bot], *-ci, github-actions …); excluded by default",
    )
    p.add_argument("--title", metavar="TEXT", help="override the report title")
    p.add_argument("--open", action="store_true", help="open the report in a browser when done")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress the summary line")
    p.add_argument("--version", action="version", version=f"gitpulse {__version__}")
    return p


def _analyze_window(
    path: str,
    *,
    since: str | None,
    until: datetime | None,
    author: str | None,
    limit: int | None,
    include_bots: bool,
    repo: str,
    branch: str,
    head: str,
    total: int,
):
    """Read + filter + aggregate one time window. Returns (Analysis, notes)."""
    commits = gitread.read_commits(path, since=since, until=until, author=author, limit=limit)
    notes: list[str] = []
    if not include_bots:
        commits, dropped = filter_bots(commits)
        if dropped:
            notes.append(f"{dropped} bot commit{'s' if dropped != 1 else ''} excluded")
    return (
        analyze(
            commits,
            repo_name=repo,
            branch=branch,
            head_sha=head,
            total_commits_in_repo=total,
        ),
        notes,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        root = gitread.ensure_repo(args.path)
        repo, branch, head = (
            gitread.repo_name(root),
            gitread.current_branch(root),
            gitread.head_sha(root),
        )
        total = gitread.count_commits(root)
    except gitread.GitError as exc:
        print(f"gitpulse: {exc}", file=sys.stderr)
        return 2

    common = {
        "author": args.author,
        "limit": None if args.compare_to else args.limit,
        "include_bots": args.include_bots,
        "repo": repo,
        "branch": branch,
        "head": head,
        "total": total,
    }

    comparison = None
    baseline = None
    notes: list[str] = []

    try:
        if args.compare_to:
            # Window A = everything since DATE. Window B = the equal-length span
            # immediately before A, derived from the real commit timestamps so we
            # never have to parse git's free-form date grammar ourselves.
            current, notes = _analyze_window(
                args.path, since=args.compare_to, until=None, **common
            )
            if current.first_commit and current.last_commit:
                start, end = current.first_commit, current.last_commit
                span = max(end - start, timedelta(days=1))
                # Half-open window [start - span, start): the -1s guard matters
                # because git's --since/--until are both inclusive, which would
                # otherwise count the boundary commit in both windows.
                boundary = start
                baseline, _ = _analyze_window(
                    args.path,
                    since=gitread.git_date(boundary - span),
                    until=boundary - timedelta(seconds=1),
                    **common,
                )
                comparison = compare(current, baseline)
            analysis = current
        else:
            analysis, notes = _analyze_window(
                args.path, since=args.since, until=None, **common
            )
    except gitread.GitError as exc:
        print(f"gitpulse: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_html(analysis, title=args.title, comparison=comparison, baseline=baseline, notes=notes),
        encoding="utf-8",
    )

    if args.json:
        json_path = Path(args.json).expanduser()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = analysis.to_dict()
        if comparison is not None:
            payload["comparison"] = [
                {
                    "metric": d.label,
                    "baseline": d.baseline,
                    "current": d.current,
                    "change": d.change,
                    "pct": None if d.pct is None else round(d.pct, 2),
                    "sentiment": d.sentiment,
                }
                for d in comparison
            ]
        payload["notes"] = notes
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not args.quiet:
        a = analysis
        print(
            f"gitpulse · {a.repo_name} · {a.commits_analyzed} commits · "
            f"{len(a.authors)} authors · +{a.added}/-{a.deleted} · bus factor {a.bus_factor}"
        )
        if comparison:
            commits_row = next((d for d in comparison if d.label == "Commits"), None)
            if commits_row:
                print(
                    f"  vs previous period: {int(commits_row.current)} commits "
                    f"({commits_row.pct:+.0f}%)" if commits_row.pct is not None else
                    f"  vs previous period: {int(commits_row.current)} commits"
                )
        for note in notes:
            print(f"  note: {note}")
        print(f"  → {out_path}")
        if args.json:
            print(f"  → {args.json}")

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
