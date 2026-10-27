# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · [SemVer](https://semver.org/).

## [1.0.0] — 2026-10-27

First stable release. Feature-complete and covered by tests on Python 3.10–3.13,
Linux/macOS/Windows.

### Added

- `gitpulse` CLI: analyse any repo in one command, `--out`, `--json`, `--since`,
  `--author`, `--limit`, `--title`, `--open`, `--quiet`.
- Self-contained HTML report (inline CSS + inline SVG, zero JavaScript):
  - KPI row (commits, contributors, churn, active days, longest streak)
  - commits-per-week bar chart (Monday-anchored, zero-filled, 30-week window)
  - 7×24 punch-card heatmap in author-local time
  - contributor ranking with relative bars
  - file hotspot / churn table
  - bus factor (lottery number)
  - Conventional Commits mix and per-extension churn
- `python -m gitpulse` entry point plus the `gitpulse` console script.
- JSON projection of every metric for dashboards and CI pipelines.
- 27 tests: parser edge cases (renames, empty repo, hostile subjects),
  aggregation maths, streak detection, HTML escaping, CLI exit codes.
- CI matrix across Python 3.10–3.13 on Linux, macOS and Windows, with a build
  gate that fails if the report ever gains a script tag or an external URL.

### Engineering notes

- History is read in a **single** `git log --numstat` pass using `\x1e` / `\x1f`
  control-character separators, so commit subjects containing newlines, pipes,
  tabs or emoji cannot corrupt parsing.
- Merge commits are excluded to avoid double-counting diffs.
- Git output is decoded as UTF-8 with `errors="replace"` — legacy commit messages
  never crash a run.
- Empty repositories and detached HEADs are handled as first-class states.
