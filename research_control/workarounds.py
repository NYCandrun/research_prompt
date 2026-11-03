"""Record research workarounds that worked, and render them for review.

Workers append one JSON line per distinct problem through the CLI. The
orchestrator's `run` command renders RESEARCH_WORKAROUNDS.md from the log, so
nobody edits the report by hand and no worker reads it.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from research_control.io import append_jsonl, atomic_write_text, load_jsonl, utc_now
from research_control.playbook import PLAYBOOK, load_sections

LOG = "tools/outputs/workarounds.jsonl"
REPORT = "RESEARCH_WORKAROUNDS.md"
APPLIES = ("host", "platform", "general")


def add_workaround(
    root: Path,
    *,
    task_id: str,
    channel: str,
    target: str,
    failure: str,
    tried: list[str],
    worked: str,
    items: int = 1,
    applies: str = "host",
    playbook_change: str = "",
    worker_id: str = "",
) -> dict[str, Any]:
    for name, value in (("task", task_id), ("channel", channel), ("target", target), ("failure", failure), ("worked", worked)):
        if not str(value).strip():
            raise ValueError(f"--{name} must not be empty")
    cleaned = [item.strip() for item in tried if item and item.strip()]
    if not cleaned:
        raise ValueError("at least one --tried entry is required: what did not work before the fix")
    if applies not in APPLIES:
        raise ValueError(f"--applies must be one of {', '.join(APPLIES)}")
    if items < 1:
        raise ValueError("--items must be at least 1")
    known = load_sections(root)
    if known and channel not in known:
        raise ValueError(f"unknown channel {channel!r}; use a key from {PLAYBOOK}: {', '.join(sorted(known))}")
    row = {
        "schema_version": "1.0.0",
        "recorded_at": utc_now(),
        "task_id": task_id,
        "worker_id": worker_id,
        "channel": channel,
        "target": target.strip(),
        "failure": failure.strip(),
        "tried": cleaned,
        "worked": worked.strip(),
        "items": items,
        "applies": applies,
        "playbook_change": playbook_change.strip(),
    }
    append_jsonl(root / LOG, row)
    render_workarounds(root)
    return row


def load_workarounds(root: Path) -> list[dict[str, Any]]:
    path = root / LOG
    return load_jsonl(path) if path.is_file() and path.stat().st_size else []


def render_workarounds(root: Path) -> Path:
    rows = load_workarounds(root)
    known = load_sections(root)
    order = list(dict.fromkeys([*known, "other"]))
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_channel[row["channel"] if row.get("channel") in known else "other"].append(row)
    lines = [
        "# Research workarounds",
        "",
        f"Generated from `{LOG}` by `python3 -m research_control run` and `workaround report`. Do not edit by hand.",
        f"Review each entry, then fold the ones worth keeping into `{PLAYBOOK}`.",
        "",
        f"{len(rows)} entries.",
        "",
    ]
    if not rows:
        lines += ["No workarounds recorded yet.", ""]
    for channel in order:
        group = by_channel.get(channel)
        if not group:
            continue
        title = known[channel]["title"] if channel in known else "Other"
        lines += [f"## {title}", ""]
        for row in sorted(group, key=lambda item: (item.get("recorded_at", ""), item.get("task_id", ""))):
            lines += [
                f"### {row.get('recorded_at', '')[:10]} · {row.get('target', '')}",
                "",
                f"- **Task:** `{row.get('task_id', '')}`" + (f" (worker `{row['worker_id']}`)" if row.get("worker_id") else ""),
                f"- **Failure:** {row.get('failure', '')}",
                "- **Tried:**",
            ]
            lines += [f"  {index}. {item}" for index, item in enumerate(row.get("tried", []), 1)]
            lines += [
                f"- **Worked:** {row.get('worked', '')}",
                f"- **Items:** {row.get('items', 1)}",
                f"- **Applies to:** {row.get('applies', '')}",
            ]
            if row.get("playbook_change"):
                lines.append(f"- **Playbook change:** {row['playbook_change']}")
            lines.append("")
    path = root / REPORT
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")
    return path
