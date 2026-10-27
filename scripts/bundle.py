#!/usr/bin/env python3
"""Bundle gitpulse into a single executable zip archive (`gitpulse.pyz`).

    python scripts/bundle.py

The result needs no installation and no dependencies: `python gitpulse.pyz .`
runs the CLI directly on any Python 3.10+ interpreter. The checksum file is
regenerated alongside so downloads can be verified.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "gitpulse.pyz"
ENTRY = b"from gitpulse.cli import main\n\nraise SystemExit(main())\n"


def main() -> int:
    sources = sorted((ROOT / "gitpulse").rglob("*.py"))
    if not sources:
        raise SystemExit("no sources found — run this from the repo root")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("__main__.py", ENTRY)

    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    (ROOT / "gitpulse.pyz.sha256").write_text(f"{digest}  gitpulse.pyz\n", encoding="utf-8")
    print(f"built {OUT.name} ({OUT.stat().st_size:,} bytes) sha256={digest[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
