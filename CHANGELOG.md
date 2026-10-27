# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · [SemVer](https://semver.org/).

## [1.1.1] — 2026-10-27

### Fixed

- **Silent data loss on Python 3.10 for UTC commits.** git's `%aI` format emits
  a bare `Z` suffix (`2025-03-30T23:00:00Z`), and `datetime.fromisoformat()`
  only learned to accept `Z` in Python 3.11. On 3.10 every UTC-timestamped
  commit raised `ValueError`, was skipped without a warning, and the report came
  back empty or under-counted — exit code 0, no error, wrong numbers.
  Timestamps now go through `gitread.parse_git_timestamp()`, which normalises
  `Z` → `+00:00` and compact `+0530` → `+05:30` before parsing. Caught by the
  CI matrix on `py3.10 / ubuntu-latest`; reproduced locally on CPython 3.10.22.

### Tests

- 53 tests (was 46): offset matrix for `Z`, lowercase `z`, `+00:00`, `+05:30`
  and compact `-0700`, garbage rejection, and an assertion that a UTC commit is
  not dropped. Suite now verified on both 3.10 and 3.13 locally.

## [1.1.0] — 2026-10-27

### Added

- **`--compare-to DATE`** — period-over-period comparison. The window since
  `DATE` is measured against the immediately preceding window of equal length,
  rendered as a colour-coded delta table (green = improved, red = regressed,
  grey = neutral) and emitted under `comparison` in `--json`. The baseline is
  derived from real commit timestamps and uses a half-open window
  `[start − span, start)`, because git's `--since`/`--until` are both inclusive
  and would otherwise count the boundary commit in both windows.
- **Bot filtering, on by default** — `dependabot[bot]`, `renovate-bot`,
  `github-actions[bot]`, `*-ci`, `snyk-bot`, `automation` and similar accounts
  are excluded before aggregation, with the excluded count surfaced as a badge
  in the report and under `notes` in JSON. `--include-bots` opts back in.
- `gitread.read_commits(..., until=...)` and `gitread.git_date()` for
  unambiguous `+0000`-offset timestamps in git arguments.
- New public API surface: `gitpulse.compare`, `gitpulse.filter_bots`,
  `gitpulse.is_bot`.
- GitHub Pages workflow that publishes a live report of the repository itself
  plus both demo pages.
- `docs/demo-comparison.html` — a second committed demo showing compare mode.

### Changed

- README now documents the real `--help` output instead of a hand-written
  approximation of it.
- Demo history generator emits ~11% bot commits and real deletions, so the
  bot filter and churn charts have something to work with.

### Fixed

- Boundary commits were double-counted between comparison windows (see the
  half-open window note above).

### Tests

- 46 tests (was 27): bot detection positive/negative matrices, `filter_bots`
  counts, comparison direction/sentiment/percentage maths, `pct is None` on a
  zero baseline, empty-baseline CLI runs, and JSON/HTML wiring for both new
  flags.

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
