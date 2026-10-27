#!/usr/bin/env bash
# push.sh — one command to publish this repo to GitHub.
#
#   bash push.sh https://github.com/<you>/gitpulse.git
#   bash push.sh git@github.com:<you>/gitpulse.git
#
# Auth: this script never asks for or stores a token itself. It relies on the
# standard git credential paths, any of which work:
#   * a personal access token in the URL:  https://<token>@github.com/you/repo.git
#   * `gh auth login` (GitHub CLI credential helper)
#   * a ~/.netrc entry, or GIT_ASKPASS / SSH keys for the git@ form
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="${1:-}"

if [[ -z "$URL" ]]; then
  cat >&2 <<'USAGE'
usage: bash push.sh <git-remote-url>

examples:
  bash push.sh https://github.com/your-name/gitpulse.git
  bash push.sh git@github.com:your-name/gitpulse.git

Create the empty repo on GitHub first (no README, no .gitignore, no license —
this repo already has them), then run the command above.
USAGE
  exit 64
fi

cd "$REPO_DIR"

# GitHub URLs sometimes get pasted with a trailing .git.git or spaces.
URL="${URL%.git}"; URL="${URL}.git"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$URL"
else
  git remote add origin "$URL"
fi

echo "→ pushing main to $URL"
GIT_TERMINAL_PROMPT=0 git push -u origin main
echo "✓ done — open ${URL%.git}"
