"""The competitor registry: who the competitors are, written by the market worker.

Dependency-free so discovery, the planner, checks, and the matrix builder can
all import it. The registry lives in the run at tools/outputs/competitors.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_control.io import atomic_write_json, utc_now

COMPETITORS_FILE = "tools/outputs/competitors.json"
KINDS = ("direct", "adjacent", "watch")
MARKET_CHANNEL = "market_competitors"


def competitor_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").casefold()).strip("-")


def load_competitors(root: Path) -> list[dict[str, Any]]:
    path = root / COMPETITORS_FILE
    if not path.is_file() or not path.stat().st_size:
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return []
    rows = value.get("competitors", []) if isinstance(value, dict) else value
    return [dict(item) for item in rows if isinstance(item, dict) and item.get("slug")]


def registry_exists(root: Path) -> bool:
    return (root / COMPETITORS_FILE).is_file() and (root / COMPETITORS_FILE).stat().st_size > 0


def _write(root: Path, competitors: list[dict[str, Any]], note: str = "") -> None:
    atomic_write_json(root / COMPETITORS_FILE, {
        "schema_version": "1.0.0",
        "updated_at": utc_now(),
        "note": note,
        "competitors": competitors,
    })


def register_competitor(
    root: Path,
    *,
    name: str,
    url: str,
    kind: str,
    reason: str,
    competing_product: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    """Add or update one competitor. The slug is stable and derived from the name."""
    if not name.strip():
        raise ValueError("--name is required")
    if not url.strip().startswith(("http://", "https://")):
        raise ValueError("--url must be an absolute http(s) URL")
    if kind not in KINDS:
        raise ValueError(f"--kind must be one of {', '.join(KINDS)}")
    if not reason.strip():
        raise ValueError("--reason is required: why this firm is in the set and what it competes on")
    competitors = load_competitors(root)
    slug = competitor_slug(name)
    record = {
        "name": name.strip(),
        "slug": slug,
        "url": url.strip(),
        "kind": kind,
        "reason": reason.strip(),
        "competing_product": competing_product.strip(),
        "registered_by": task_id,
        "registered_at": utc_now(),
    }
    replaced = False
    for index, item in enumerate(competitors):
        if item.get("slug") == slug:
            competitors[index] = {**item, **record, "registered_at": item.get("registered_at", record["registered_at"])}
            replaced = True
    if not replaced:
        competitors.append(record)
    _write(root, competitors)
    return {**record, "updated": replaced, "count": len(competitors)}


def register_none(root: Path, *, evidence: str, task_id: str = "") -> dict[str, Any]:
    """Record that the market worker found no competitors, with the searches that establish it."""
    if not evidence.strip():
        raise ValueError("--evidence is required: the searches that establish there are no competitors")
    if load_competitors(root):
        raise ValueError("competitors are registered; remove the file by hand only if the registry is wrong")
    _write(root, [], note=f"no competitors found: {evidence.strip()} (recorded by {task_id or 'unknown task'})")
    return {"competitors": 0, "note": evidence.strip()}


def competitor_by_slug(root: Path, slug: str) -> dict[str, Any] | None:
    return next((item for item in load_competitors(root) if item.get("slug") == slug), None)


def subject_metadata(root: Path, subject: str) -> dict[str, str]:
    """Source metadata for a competitor subject; the slug must be registered first."""
    record = competitor_by_slug(root, competitor_slug(subject))
    if record is None:
        known = ", ".join(item["slug"] for item in load_competitors(root)) or "none registered"
        raise ValueError(
            f"unknown competitor subject {subject!r}; register it first with `discovery competitor` (known: {known})"
        )
    return {"subject": record["slug"], "subject_name": record["name"], "subject_kind": record.get("kind", "")}
