"""Allows ``python -m gitpulse`` to behave exactly like the ``gitpulse`` console script."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
