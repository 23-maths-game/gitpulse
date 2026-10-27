# ⚡ gitpulse

**Zero-dependency git repository intelligence.** Turn any repository's history into a single, self-contained interactive HTML report — dependency-free, network-free, framework-free.

[![CI](https://github.com/your-username/gitpulse/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/gitpulse/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](pyproject.toml)

```bash
gitpulse .                                  # analyse the repo you're standing in
gitpulse . --compare-to "3 months ago"      # this quarter vs last quarter
gitpulse ~/code/api --since "6 months ago" --json stats.json --open
```

> 📊 **[Full demo report →](docs/demo-report.html)** · **[Period-comparison demo →](docs/demo-comparison.html)**
> (both generated from a 455-commit synthetic history with 4 humans and 2 bots)

---

## Why another git stats tool?

Most tools in this space want to be a web service, need Node/Go binaries, or phone
home with your commit data. `gitpulse` is the opposite:

| | gitpulse | Typical alternatives |
|---|---|---|
| Dependencies | **none** (stdlib only) | pip/npm/docker install |
| Output | **one HTML file**, inline CSS + SVG | hosted dashboard / screenshots |
| Network calls | **zero** | analytics, fonts, CDNs |
| Runtime | one `git log` pass | per-commit queries |
| Data leaves your machine | **never** | often |

It exists so you can drop a repo-health report into a PR, a CI artifact, a
retro deck, or a README without a single `npm install`.

---

## Install

```bash
# straight from source (no build step)
git clone https://github.com/your-username/gitpulse.git
cd gitpulse
python -m gitpulse --version

# or install the CLI globally
pip install .
```

No third-party packages are required. Development extras only:

```bash
pip install -e ".[dev]"   # pytest + ruff
```

### Standalone single file (no install, no clone)

[`gitpulse.pyz`](gitpulse.pyz) is the whole tool bundled as an 18 KB executable
zip archive. Download it and run it anywhere Python 3.10+ exists:

```bash
python gitpulse.pyz /path/to/repo -o report.html
sha256sum -c gitpulse.pyz.sha256   # verify the download
```

Rebuild it after changing the source with `python scripts/bundle.py`.

---

## Usage

```
usage: gitpulse [-h] [-o OUT] [--json FILE] [--since DATE] [--author PATTERN] [--limit N]
                [--compare-to DATE] [--include-bots] [--title TEXT] [--open] [-q] [--version]
                [path]

positional arguments:
  path               path inside a git repo (default: .)

options:
  -h, --help         show this help message and exit
  -o, --out OUT      HTML output path
  --json FILE        also write the raw metrics as JSON
  --since DATE       limit history, e.g. '2024-01-01' or '6 months ago'
  --author PATTERN   only commits by this author (regex as git accepts it)
  --limit N          analyse at most N commits
  --compare-to DATE  compare the window since DATE against the preceding window of equal length
                     (e.g. '3 months ago' = this quarter vs last quarter)
  --include-bots     count automation accounts (dependabot[bot], *-ci, github-actions …); excluded
                     by default
  --title TEXT       override the report title
  --open             open the report in a browser when done
  -q, --quiet        suppress the summary line
  --version          show program's version number and exit
```

### Recipes

```bash
# Last quarter, only one contributor, open when done
gitpulse . --since "3 months ago" --author "ada@example.com" --open

# Feed a dashboard / CI job
gitpulse . -q --json artifacts/metrics.json -o artifacts/report.html

# Is the team speeding up or slowing down?
gitpulse . --compare-to "3 months ago" --open

# Ignore CI noise and measure humans only (default), or count everything
gitpulse . --include-bots -o with-bots.html

# Compare two repos
for r in api web; do gitpulse ~/code/$r -o reports/$r.html -q; done

# As a library
python -c "from gitpulse import read_commits, analyze; print(analyze(read_commits('.')).bus_factor)"
```

---

## What's in the report

| Panel | What it tells you |
|---|---|
| **KPI row** | commits analysed, contributors, churn (+/−), active days, longest streak |
| **Commits per week** | Monday-anchored ISO weeks, zero-filled gaps, 30-week window |
| **Punch card** | 7×24 heatmap of commit hours in the *author's* timezone |
| **Contributors** | ranked by commits, with relative bars |
| **Hotspots** | the files that get touched most — your refactor backlog |
| **Bus factor** | fewest authors holding >50% of commits (a.k.a. lottery number) |
| **Commit prefixes** | Conventional Commits mix (`feat`, `fix`, `docs`, …) |
| **File types** | churn grouped by extension |
| **Period comparison** | with `--compare-to`: baseline vs current vs delta, colour-coded by whether the change is good or bad |

### Bot commits are excluded by default

`dependabot[bot]`, `renovate-bot`, `github-actions[bot]`, `*-ci` and friends are
filtered out before any metric is computed — otherwise a single dependency bot
out-commits the team and pushes your bus factor to a meaningless `1`. The report
tells you how many were dropped, and `--include-bots` brings them back.

Everything is inline SVG — it renders identically offline, in a sandboxed
iframe, in an email attachment, or committed as a CI artifact.

---

## How it works

```
gitpulse/gitread.py   subprocess + parsing   ── one `git log --numstat` pass
gitpulse/metrics.py   pure aggregation       ── no I/O, fully unit-tested
gitpulse/render.py    HTML + SVG rendering   ── escaped, self-contained
gitpulse/cli.py       argument parsing
```

Three deliberate engineering choices:

1. **One subprocess call, not N.** Headers and numstat come back in a single
   `git log` invocation, so a 50k-commit history costs one fork, not 50k.
2. **Control-character separators.** Records use `\x1e` / `\x1f` instead of
   newlines or pipes, so subjects containing newlines, `|`, tabs, or emoji
   parse correctly. (And we split on `"\n"` — never `str.splitlines()`, which
   treats `\x1c`–`\x1e` as line boundaries and silently shreds records.)
3. **Merges are excluded.** A merge duplicates the same diff under a second
   SHA; counting it would inflate churn in every downstream metric.

---

## Development

```bash
make test        # pytest -q
make lint        # ruff check .
make report      # analyse this repo -> gitpulse-report.html
make demo        # rebuild docs/demo-report.html from a synthetic history
```

Design rules for contributors:

- **No runtime dependencies.** Stdlib only, forever. That's the whole pitch.
- **No network, ever.** No fonts, no CDNs, no telemetry, no "phone home".
- `metrics.py` must stay pure — data in, data out, no filesystem, no subprocess.
- Every user-controlled string that reaches HTML goes through escaping.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT © contributors. See [LICENSE](LICENSE).
