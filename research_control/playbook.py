"""Copy the relevant RESEARCH_PLAYBOOK.md sections into task packets.

Workers never read the playbook. The packet writer selects the general
sections plus the sections keyed to the task's channels, so each worker's
brief carries only what it can use. This module also holds the rule for
blocked records: a blocked channel or source lists the approaches tried.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PLAYBOOK = "RESEARCH_PLAYBOOK.md"
MIN_TRIED = 2
GENERAL = ("mandate", "off-limits", "workaround-log")
EVERY_CHANNEL = "general"
HEADING = re.compile(r"^## (?P<title>.+?)(?:\s*\((?P<keys>[a-z0-9_,\s-]+)\))?\s*$")
CHANNEL_EXTRAS = {
    "company_site": ["archives"],
    "sitemaps": ["archives"],
    "newsroom_blog": ["archives"],
    "market_competitors": ["archives"],
    "video": ["transcription"],
    "podcasts": ["transcription"],
}
TASK_KEYS = {
    "source_discovery": [*GENERAL, EVERY_CHANNEL],
    "alternate_copies": [*GENERAL, EVERY_CHANNEL, "archives", "pdf"],
    "brand_guide": [*GENERAL, EVERY_CHANNEL, "company_site"],
    "scope": [*GENERAL],
    "capture": [*GENERAL, EVERY_CHANNEL],
    "extraction": [*GENERAL, "pdf", "tooling"],
}


def distinct_tried(tried: Any) -> list[str]:
    """Normalize 'approach -> result' entries, dropping blanks and case-insensitive duplicates."""
    cleaned: list[str] = []
    for item in tried or []:
        text = " ".join(str(item).split())
        if text and text.casefold() not in {existing.casefold() for existing in cleaned}:
            cleaned.append(text)
    return cleaned


def require_tried(tried: Any, subject: str) -> list[str]:
    cleaned = distinct_tried(tried)
    if len(cleaned) < MIN_TRIED:
        raise ValueError(
            f"{subject}: a blocked record needs at least {MIN_TRIED} distinct approaches in --tried, "
            f"each written as 'approach -> result'; got {len(cleaned)}"
        )
    return cleaned


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")


def sections(text: str) -> dict[str, dict[str, Any]]:
    """Map every key to {title, keys, body}; a section is reachable by each key in its heading."""
    out: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        if current is None:
            return
        current["body"] = "\n".join(body).strip()
        for key in current["keys"]:
            out.setdefault(key, current)

    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match:
            flush()
            keys = [item.strip() for item in (match["keys"] or "").split(",") if item.strip()]
            title = match["title"].strip()
            current = {"title": title, "keys": keys or [_slug(title)], "body": ""}
            body = []
        elif current is not None:
            body.append(line)
    flush()
    return out


def load_sections(root: Path) -> dict[str, dict[str, Any]]:
    path = root / PLAYBOOK
    return sections(path.read_text(encoding="utf-8")) if path.is_file() else {}


def task_channels(task: dict[str, Any]) -> list[str]:
    """Channels a task works on: its `channels` input or metadata, or the channel of each source input."""
    found: list[str] = []
    metadata = task.get("metadata") or {}
    for value in metadata.get("channels") or []:
        found.append(str(value))
    for item in task.get("inputs") or []:
        if not isinstance(item, dict):
            continue
        if item.get("id") == "channels" and isinstance(item.get("value"), list):
            found.extend(str(value) for value in item["value"])
        elif item.get("channel"):
            found.append(str(item["channel"]))
    return list(dict.fromkeys(found))


def section_keys(task: dict[str, Any]) -> list[str]:
    """Playbook keys for a task, in packet order. Empty when the task does no research access."""
    task_type = str(task.get("task_type") or "")
    keys = list(TASK_KEYS.get(task_type, []))
    if not keys:
        return []
    channels = task_channels(task)
    # An alternate-copies pass lists every channel; its own section set already covers it.
    if task_type in {"source_discovery", "capture", "brand_guide"}:
        for channel in channels:
            keys.append(channel)
            keys += CHANNEL_EXTRAS.get(channel, [])
    if task_type == "capture":
        for item in task.get("inputs") or []:
            if isinstance(item, dict) and str(item.get("url") or "").casefold().endswith(".pdf"):
                keys.append("pdf")
    return list(dict.fromkeys(keys))


def playbook_for_task(root: Path, task: dict[str, Any]) -> tuple[list[str], str]:
    """Return (keys used, Markdown block) for the packet. A missing playbook or key is skipped."""
    available = load_sections(root)
    if not available:
        return [], ""
    used: list[str] = []
    seen: set[int] = set()
    parts: list[str] = []
    for key in section_keys(task):
        section = available.get(key)
        if section is None or id(section) in seen:
            continue
        seen.add(id(section))
        used.append(key)
        parts.append(f"### {section['title']}\n\n{section['body']}")
    if not parts:
        return [], ""
    block = (
        "## Research playbook\n\n"
        f"These sections are copied from `{PLAYBOOK}` for this task. Follow the mandate.\n\n"
        + "\n\n".join(parts)
        + "\n"
    )
    return used, block
