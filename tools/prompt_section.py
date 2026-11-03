#!/usr/bin/env python3
"""Print numbered sections of the README prompt verbatim.

Examples:
  python3 tools/prompt_section.py 10          # section 10 and all its subsections
  python3 tools/prompt_section.py -1 7 8      # several sections in order
  python3 tools/prompt_section.py --list      # every section with line range and size
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_control.prompt_sections import listing, section_text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keys", nargs="*", help="section numbers such as -1, 0, 10, 19, or intro")
    parser.add_argument("--list", action="store_true", help="list sections instead of printing them")
    parser.add_argument("--file", type=Path, default=Path(__file__).resolve().parents[1] / "README.md")
    args = parser.parse_args()
    if args.list or not args.keys:
        sys.stdout.write(listing(args.file))
        return
    try:
        sys.stdout.write(section_text(args.file, args.keys))
    except KeyError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
