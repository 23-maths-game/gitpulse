"""gitpulse — zero-dependency git repository intelligence."""

from .gitread import GitError, ensure_repo, read_commits
from .metrics import analyze
from .render import render_html

__version__ = "1.1.0"
__all__ = ["GitError", "__version__", "analyze", "ensure_repo", "read_commits", "render_html"]
