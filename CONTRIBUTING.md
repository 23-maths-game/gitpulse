# Contributing to gitpulse

Thanks for being here. The bar is high, the surface is small — that's on purpose.

## Ground rules

1. **No runtime dependencies.** If your feature needs a package, it needs a
   design discussion first. Stdlib only is the product, not an accident.
2. **No network calls.** No CDNs, fonts, telemetry, or "anonymous usage stats".
   The CI job fails the build if the rendered report contains a URL.
3. **`metrics.py` stays pure.** Data in, data out. No filesystem, no subprocess,
   no `datetime.now()` — that belongs in the CLI layer.
4. **Escape everything that reaches HTML.** Any git-provided string (paths,
   author names, subjects) is untrusted input.
5. **Never `str.splitlines()` on git output.** It treats `\x1c`–`\x1e` as line
   boundaries and will silently corrupt record parsing. Split on `"\n"`.

## Setup

```bash
git clone https://github.com/23-maths-game/gitpulse.git
cd gitpulse
pip install -e ".[dev]"
make test
```

## Before you open a PR

```bash
make lint     # ruff
make test     # pytest
make demo     # regenerate docs/demo-report.html if rendering changed
```

- Add or update tests for any behaviour change — `tests/` mirrors the module
  layout, so `metrics.py` changes belong in `tests/test_metrics.py`.
- Keep the diff focused. Unrelated refactors make review slower.
- If you change rendered output, rebuild the demo report so reviewers can see it
  in the diff, and mention it in the PR description.

## Commit messages

Conventional Commits, please — the tool literally analyses them:

```
feat(cli): add --branch filter
fix(parse): handle renames in numstat
docs(readme): document --since
```

## Reporting bugs

Include: your OS, `python --version`, `git --version`, the exact command, and
the full traceback. If parsing is wrong, paste the raw output of:

```bash
git log --pretty=format:'%H%x1f%an%x1f%ae%x1f%aI%x1f%s' --numstat --no-merges | head -40
```

## License

By contributing you agree your work is released under the MIT License.
