"""Copy the relevant RESEARCH_PLAYBOOK.md sections into task packets.

Workers never read the playbook. The packet writer selects the general
sections plus the sections keyed to the task's channel, so each packet carries
only what that worker can use.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

PLAYBOOK = "RESEARCH_PLAYBOOK.md"
MIN_TRIED = 2


def distinct_tried(tried: Any) -> list[str]:
    """Normalize a list of 'approach -> result' entries, dropping blanks and case-insensitive duplicates."""
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
GENERAL = ("mandate", "off-limits", "workaround-log")
EVERY_CHANNEL = "general"
HEADING = re.compile(r"^## (?P<title>.+?)(?:\s*\((?P<keys>[a-z0-9_,\s-]+)\))?\s*$")
CHANNEL_EXTRAS = {
    "competitors": ["archives"],
    "company_site": ["archives"],
    "sitemaps": ["archives"],
    "newsroom_blog": ["archives"],
    "video": ["transcription"],
    "podcasts": ["transcription"],
}
MEDIA_CHANNELS = {"video", "podcasts"}


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")


def sections(text: str) -> dict[str, dict[str, Any]]:
    """Map every key to {title, keys, body}. A section is reachable by each key in its heading."""
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
    if not path.is_file():
        return {}
    return sections(path.read_text(encoding="utf-8"))


def _task_channel(task: dict[str, Any]) -> str | None:
    metadata = task.get("metadata") or {}
    if metadata.get("channel"):
        return str(metadata["channel"])
    for item in task.get("inputs") or []:
        if isinstance(item, dict):
            if item.get("channel"):
                return str(item["channel"])
            if item.get("id") == "channel" and item.get("value"):
                return str(item["value"])
    return None


def _task_wants_pdf(task: dict[str, Any]) -> bool:
    for item in task.get("inputs") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").casefold()
        kind = str(item.get("source_kind") or "").casefold()
        if url.endswith(".pdf") or "pdf" in kind or "document" in kind:
            return True
    return False


def section_keys(task: dict[str, Any]) -> list[str]:
    """Playbook keys for a task, in packet order. Empty when the task does no research access."""
    task_type = str(task.get("task_type") or "")
    keys: list[str] = []
    if task_type in {"source_discovery", "capture", "brand_guide"}:
        keys += [*GENERAL, EVERY_CHANNEL]
        channel = _task_channel(task) or ("company_site" if task_type == "brand_guide" else None)
        if channel and channel.startswith("competitor:"):
            channel = "competitors"
        if channel:
            keys.append(channel)
            keys += CHANNEL_EXTRAS.get(channel, [])
        if task_type == "capture" and _task_wants_pdf(task):
            keys.append("pdf")
    elif task_type == "extraction":
        keys += [*GENERAL, "pdf", "tooling"]
    return list(dict.fromkeys(keys))


def playbook_for_task(root: Path, task: dict[str, Any]) -> tuple[list[str], str]:
    """Return (keys used, Markdown block) for the packet. Missing playbook or keys are skipped, not fatal."""
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
