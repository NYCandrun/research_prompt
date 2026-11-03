"""Locate and print numbered sections of the README prompt without retyping them."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
NUMBERED = re.compile(r"^(-?\d+)(?:\.\d+)*\.?(?:\s|$)")
INTRO = "intro"


@dataclass
class Section:
    key: str
    title: str
    start: int  # 0-based line index, inclusive
    end: int  # 0-based line index, exclusive

    def text(self, lines: list[str]) -> str:
        return "\n".join(lines[self.start:self.end]).rstrip() + "\n"


def _boundaries(lines: list[str]) -> list[tuple[int, str | None, str]]:
    """Return (line, key, title) for every heading. Key None means 'attach to next numbered section'."""
    found: list[tuple[int, str | None, str]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if not match:
            continue
        level, title = len(match.group(1)), match.group(2)
        number = NUMBERED.match(title)
        if number:
            found.append((index, number.group(1), title))
        elif level == 1:
            found.append((index, None, title))
    return found


def sections(text: str) -> list[Section]:
    """Split the prompt into the intro plus one Section per top-level number, in document order."""
    lines = text.splitlines()
    raw = _boundaries(lines)
    # Attach unnumbered level-1 headings to the numbered section that follows them.
    keyed: list[tuple[int, str, str]] = []
    pending: list[tuple[int, str]] = []
    for line, key, title in raw:
        if key is None:
            pending.append((line, title))
            continue
        if pending and keyed:
            keyed.append((pending[0][0], key, pending[0][1]))
        pending = []
        keyed.append((line, key, title))
    out: list[Section] = []
    first_numbered = keyed[0][0] if keyed else len(lines)
    if first_numbered > 0:
        out.append(Section(INTRO, lines[0].lstrip("# ").strip() if lines else INTRO, 0, first_numbered))
    for position, (line, key, title) in enumerate(keyed):
        if out and out[-1].key == key:
            continue
        end = len(lines)
        for next_line, next_key, _ in keyed[position + 1:]:
            if next_key != key:
                end = next_line
                break
        out.append(Section(key, title, line, end))
    return out


def section(text: str, key: str) -> Section:
    for item in sections(text):
        if item.key == key:
            return item
    raise KeyError(f"no section numbered {key}")


def section_text(path: Path, keys: list[str]) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    return "".join(section(text, key).text(lines) + "\n" for key in keys).rstrip() + "\n"


def listing(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows = ["key    lines        ~tokens  title"]
    for item in sections(text):
        chars = sum(len(line) + 1 for line in lines[item.start:item.end])
        rows.append(f"{item.key:<6} {item.start + 1:>5}-{item.end:<6} {chars // 4:>7}  {item.title}")
    return "\n".join(rows) + "\n"
