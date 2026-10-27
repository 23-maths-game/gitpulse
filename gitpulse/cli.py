"""Command-line interface: ``gitpulse [PATH] [options]``."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from . import __version__, gitread
from .metrics import analyze
from .render import render_html


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gitpulse",
        description="Zero-dependency git repository intelligence — one self-contained HTML report.",
        epilog="Examples:\n"
        "  gitpulse                      # analyse the current repo\n"
        "  gitpulse ~/code/api --since '6 months ago'\n"
        "  gitpulse . --json stats.json --out report.html",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", nargs="?", default=".", help="path inside a git repo (default: .)")
    p.add_argument("-o", "--out", default="gitpulse-report.html", help="HTML output path")
    p.add_argument("--json", metavar="FILE", help="also write the raw metrics as JSON")
    p.add_argument("--since", metavar="DATE", help="limit history, e.g. '2024-01-01' or '6 months ago'")
    p.add_argument("--author", metavar="PATTERN", help="only commits by this author (regex as git accepts it)")
    p.add_argument("--limit", type=int, metavar="N", help="analyse at most N commits")
    p.add_argument("--title", metavar="TEXT", help="override the report title")
    p.add_argument("--open", action="store_true", help="open the report in a browser when done")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress the summary line")
    p.add_argument("--version", action="version", version=f"gitpulse {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        root = gitread.ensure_repo(args.path)
        commits = gitread.read_commits(
            args.path, since=args.since, author=args.author, limit=args.limit
        )
    except gitread.GitError as exc:
        print(f"gitpulse: {exc}", file=sys.stderr)
        return 2

    analysis = analyze(
        commits,
        repo_name=gitread.repo_name(root),
        branch=gitread.current_branch(root),
        head_sha=gitread.head_sha(root),
        total_commits_in_repo=gitread.count_commits(root),
    )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(analysis, title=args.title), encoding="utf-8")

    if args.json:
        json_path = Path(args.json).expanduser()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(analysis.to_dict(), indent=2), encoding="utf-8")

    if not args.quiet:
        a = analysis
        print(
            f"gitpulse · {a.repo_name} · {a.commits_analyzed} commits · "
            f"{len(a.authors)} authors · +{a.added}/-{a.deleted} · bus factor {a.bus_factor}"
        )
        print(f"  → {out_path}")
        if args.json:
            print(f"  → {args.json}")

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
