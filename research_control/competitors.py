"""Competitor list written by the scope task and consumed by the planner and discovery.

Kept dependency-free so checks, discovery, and the planner can all import it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

COMPETITORS_FILE = "tools/outputs/competitors.json"
COMPETITOR_PREFIX = "competitor:"
COMPETITOR_CHANNEL = re.compile(r"^competitor:[a-z0-9][a-z0-9-]*$")


def competitor_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").casefold()).strip("-")


def load_competitors(root: Path) -> list[dict[str, Any]]:
    """Competitors with a normalized slug. Malformed files load as empty; the scope validator reports them."""
    path = root / COMPETITORS_FILE
    if not path.is_file() or not path.stat().st_size:
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return []
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or not str(item.get("name", "")).strip():
            continue
        record = dict(item)
        record["name"] = str(item["name"]).strip()
        record["slug"] = competitor_slug(str(item.get("slug") or record["name"]))
        record["watch_list"] = bool(item.get("watch_list", False))
        out.append(record)
    return out


def competitor_channels(root: Path) -> list[str]:
    """One discovery channel per researched competitor. Watch-list entries get no channel."""
    return [f"{COMPETITOR_PREFIX}{item['slug']}" for item in load_competitors(root) if not item["watch_list"]]


def competitor_for_channel(root: Path, channel: str) -> dict[str, Any] | None:
    if not channel.startswith(COMPETITOR_PREFIX):
        return None
    slug = channel[len(COMPETITOR_PREFIX):]
    return next((item for item in load_competitors(root) if item["slug"] == slug), {"name": slug, "slug": slug, "url": ""})


def validate_competitors(root: Path, scope_text: str) -> tuple[list[str], list[str]]:
    """Return (failures, unknowns) for the competitor file against the scope document."""
    path = root / COMPETITORS_FILE
    if not path.is_file() or not path.stat().st_size:
        return [], [f"{COMPETITORS_FILE} is missing or empty; write [] when the scope records that there are no competitors"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        return [f"{COMPETITORS_FILE}: invalid JSON: {error}"], []
    if not isinstance(value, list):
        return [f"{COMPETITORS_FILE} must be a JSON list"], []
    failures: list[str] = []
    slugs: set[str] = set()
    lowered = scope_text.casefold()
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict):
            failures.append(f"competitor {index}: not an object")
            continue
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if not name:
            failures.append(f"competitor {index}: missing name")
        if not url.startswith(("http://", "https://")):
            failures.append(f"competitor {index}: url must be absolute http(s)")
        if not str(item.get("reason", "")).strip():
            failures.append(f"competitor {index}: missing reason")
        slug = competitor_slug(str(item.get("slug") or name))
        if slug in slugs:
            failures.append(f"competitor {index}: duplicate slug {slug}")
        slugs.add(slug)
        if name and name.casefold() not in lowered:
            failures.append(f"competitor {name!r} is not discussed in 00-scope.md")
    return failures, []
