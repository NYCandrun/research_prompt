"""Review tables for the citation claim reviewers, built from the citation map by script.

The citation map is a machine structure: every deep link appears twice and no
claim or quote appears at all, so a reviewer who reads it still has to open a
fact row for each citation. These tables give each reviewer its half of the
citations in reading order, with the words before each citation, its fact IDs,
and its source note, followed by an index of every cited fact's claim, quote,
and source. One file per reviewer, nothing read twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_control.io import atomic_write_text, load_json, resolve_pattern, utc_now
from research_control.validators.facts import load_fact_tables

CITATION_MAPS = "tools/outputs/citation-map-*.json"
TABLES = {"a": "tools/outputs/citation-review-a.md", "b": "tools/outputs/citation-review-b.md"}
QUOTE_LIMIT = 600


def _clip(text: str, limit: int = QUOTE_LIMIT) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + " [...]"


def _facts(root: Path) -> dict[str, dict[str, str]]:
    rows = load_fact_tables(sorted((root / "02-facts").glob("*.md")))
    return {str(row.get("fact_id", "")).strip(): row for row in rows if str(row.get("fact_id", "")).strip()}


def _note_line(note: dict[str, Any] | None) -> str:
    if not note:
        return "note: none"
    source_ids = note.get("source_ids") or ([note.get("source_id")] if note.get("source_id") else [])
    parts = [f"note {note.get('n')}", str(note.get("publisher") or note.get("title") or "").strip(), str(note.get("date") or "").strip(),
             f"grade {note.get('grade')}" if note.get("grade") else "", ", ".join(str(item) for item in source_ids)]
    return " · ".join(part for part in parts if part)


def build_review_tables(root: Path) -> dict[str, Any]:
    maps = sorted(resolve_pattern(root, CITATION_MAPS))
    citations: list[tuple[str, dict[str, Any], dict[str, Any] | None]] = []
    for path in maps:
        value = load_json(path)
        if not isinstance(value, dict):
            continue
        notes = {note.get("n"): note for note in value.get("notes", []) if isinstance(note, dict)}
        document = str(value.get("document") or path.name)
        for citation in value.get("citations", []):
            if isinstance(citation, dict):
                citations.append((document, citation, notes.get(citation.get("n"))))
    facts = _facts(root)
    half = (len(citations) + 1) // 2
    halves = {"a": citations[:half], "b": citations[half:]}
    documents = sorted({document for document, _citation, _note in citations})
    result: dict[str, Any] = {"schema_version": "1.0.0", "built_at": utc_now(), "citations": len(citations), "documents": documents}
    for label, items in halves.items():
        cited: list[str] = []
        lines = [
            f"# Citation review table {label.upper()}",
            "",
            f"Built by script on {utc_now()[:10]} from {', '.join(f'`{item}`' for item in documents) or 'no citation map'} "
            f"and `02-facts/`. This half holds citations {items[0][1].get('n') if items else '-'} onward in reading order "
            f"({len(items)} of {len(citations)}). For each: the citation number, the words before it, its fact IDs, and "
            "its source note. The cited facts' claims, quotes, and sources follow. Judge from this file; open the rendered "
            "brief, a fact row, or a capture only when it is not enough.",
            "",
            "## Citations in reading order",
            "",
        ]
        for index, (document, citation, note) in enumerate(items, 1):
            fact_ids = [str(item) for item in citation.get("facts", [])]
            for fact_id in fact_ids:
                if fact_id not in cited:
                    cited.append(fact_id)
            heading = f"### {index}. citation {citation.get('n')}"
            if len(documents) > 1:
                heading += f" in `{document}`"
            lines += [
                heading,
                f"- before it: {_clip(citation.get('place') or '(no placement text recorded)', 300)}",
                f"- facts: {', '.join(fact_ids) or 'none'}",
                f"- {_note_line(note)}",
                "",
            ]
        lines += ["## Cited facts", ""]
        for fact_id in cited:
            row = facts.get(fact_id)
            if row is None:
                lines += [f"### {fact_id}", "- not found in `02-facts/` (check whether it was withdrawn)", ""]
                continue
            lines += [
                f"### {fact_id}",
                f"- claim: {_clip(row.get('claim', ''))}",
                f"- quote: \"{_clip(row.get('verbatim_quote', '')).strip(chr(34) + '“”')}\"",
                f"- source: {row.get('source_id', '')} · {row.get('source_date', '') or 'undated'} · grade {row.get('grade', '')} · "
                f"about {row.get('about', '')} · said by {row.get('said_by', '')} · at {_clip(row.get('location', ''), 120)}",
                f"- verdict: {row.get('verdict', '')}" if row.get("verdict") else "",
                "",
            ]
        atomic_write_text(root / TABLES[label], "\n".join(line for line in lines if line is not None).rstrip() + "\n")
        result[label] = {"citations": len(items), "facts": len(cited), "path": TABLES[label]}
    return result
