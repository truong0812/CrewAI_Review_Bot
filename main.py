"""Backward-compatible entry point. Use 'pr-review review' for the CLI instead."""

import sys
import os

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import cli  # noqa: E402
from engine import parse_verdict  # noqa: F401 — re-export for backward compat

if __name__ == "__main__":
    args = ["review"] + sys.argv[1:]
    sys.argv = [sys.argv[0]] + args
    cli()
