"""
Run local quality checks in one command.

Usage:
    python scripts/verify.py
"""

from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> int:
    print(f"-> {' '.join(cmd)}")
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    checks = [
        [sys.executable, "-m", "ruff", "check", "tests", "scripts"],
        [sys.executable, "-m", "pytest"],
    ]

    for cmd in checks:
        code = run(cmd)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
