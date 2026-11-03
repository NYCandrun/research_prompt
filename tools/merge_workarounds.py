#!/usr/bin/env python3
"""Rebuild RESEARCH_WORKAROUNDS.md from every part in workarounds/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_control.workarounds import merge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    path, count, problems = merge(args.root.resolve())
    for problem in problems:
        print(f"warning: {problem}")
    print(f"workarounds entries={count} warnings={len(problems)} output={path}")


if __name__ == "__main__":
    main()
