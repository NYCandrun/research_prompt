"""Fill the competitor comparison matrix from the fact store, by script.

Rows are the company and each registered competitor. Cells list the fact IDs
that bear on each column, grouped by source date, so every cell entry has a
source and a date. The script writes no scores and no judgments: the writer
of `05-synthesis/competitors.md` defines the rubric, scores each cell under
it, and marks every ahead, level, or behind judgment as inference.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from research_control.competitors import load_competitors
from research_control.io import atomic_write_json, atomic_write_text, utc_now
from research_control.validators.facts import load_fact_tables

MATRIX_DRAFT = "05-synthesis/competitors-matrix-draft.md"
MATRIX_JSON = "tools/outputs/competitor-matrix.json"

COLUMNS: list[tuple[str, str, tuple[str, ...]]] = [
    ("sells", "What it sells", (
        "product", "platform", "offering", "service", "capability", "feature", "module", "solution", "agent", "workflow",
        "api", "model", "sells", "offers", "launch", "positioning", "category",
    )),
    ("buyers", "Who it sells to", (
        "customer", "buyer", "enterprise", "mid-market", "smb", "agency", "agencies", "segment", "industry", "vertical",
        "persona", "team", "role", "audience", "market", "sells to", "serves",
    )),
    ("packaging", "Packaging and pricing", (
        "pricing", "price", "plan", "tier", "free", "trial", "credit", "seat", "usage", "subscription", "contract",
        "rate", "fee", "cost", "$", "packaging", "self-serve", "demo", "quote",
    )),
    ("access", "Developer and data access", (
        "api", "sdk", "mcp", "integration", "connector", "export", "webhook", "data access", "open source",
        "repository", "github", "documentation", "docs", "plugin",
    )),
    ("proof", "Proof points", (
        "customer", "case study", "result", "metric", "percent", "%", "revenue", "arr", "funding", "raised", "valuation",
        "headcount", "employees", "review", "rating", "analyst", "award", "soc 2", "iso", "certif", "partner",
    )),
    ("direction", "Direction and launches", (
        "launch", "announce", "roadmap", "plan", "aim", "will", "acquisition", "acquire", "expand", "new", "beta",
        "introduc", "release", "hire", "opening", "strategy", "direction",
    )),
]
RUBRIC_TEMPLATE = {
    "What it sells": "a. core offering is documented; b. second product line or module; c. in-product automation or AI; d. services alongside product; e. named integrations or ecosystem",
    "Who it sells to": "a. enterprise plan or SSO; b. self-serve plan below enterprise; c. agency or partner program; d. named buyer roles beyond the obvious; e. named industries or verticals",
    "Packaging and pricing": "a. a dollar price on the company's own pages; b. free plan, trial, or audit without a sales call; c. a public usage unit; d. no per-seat fee on at least one plan; e. paid expert help or services",
    "Developer and data access": "a. documented API; b. SDK or MCP server; c. write actions through API; d. export or BI route; e. API below the top tier",
    "Proof points": "a. named customer with a measured result on the company's own pages; b. customer count or share claim; c. third-party rating or analyst recognition; d. security attestation; e. disclosed funding, revenue, or parent",
    "Direction and launches": "a. dated launch in the last year; b. stated roadmap or aim; c. acquisition or funding in the last two years; d. hiring in product or engineering; e. positioning change with dates",
}


def _match(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in terms)


def _subject_of(row: dict[str, str], competitors: list[dict[str, Any]]) -> str:
    """The competitor slug a fact is about, 'market' for market facts, or 'company' otherwise."""
    about = str(row.get("about", "")).casefold()
    if about.startswith("market"):
        return "market"
    for item in competitors:
        name = str(item.get("name", "")).casefold()
        if name and (about == name or about.startswith(f"{name} (") or about.startswith(f"{name},")):
            return item["slug"]
    return "company"


def _describes_company(row: dict[str, str], competitors: list[dict[str, Any]]) -> str | None:
    """The competitor slug when the fact is a competitor's own words about the company."""
    said_by = str(row.get("said_by", "")).casefold()
    about = str(row.get("about", "")).casefold()
    for item in competitors:
        name = str(item.get("name", "")).casefold()
        if name and name in said_by and not about.startswith(name):
            return item["slug"]
    return None


def build_matrix(root: Path, company_name: str = "") -> dict[str, Any]:
    competitors = sorted(load_competitors(root), key=lambda item: (item.get("kind") != "direct", item.get("name", "")))
    rows = load_fact_tables(sorted((root / "02-facts").glob("*.md")))
    cells: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    about_company: dict[str, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        fact_id = str(row.get("fact_id", "")).strip()
        if not fact_id:
            continue
        subject = _subject_of(row, competitors)
        describer = _describes_company(row, competitors)
        if describer and subject == "company":
            about_company[describer].append(fact_id)
            continue
        if subject == "market":
            continue
        date = str(row.get("source_date", "")).strip() or "undated"
        text = f"{row.get('topics', '')} {row.get('claim', '')} {row.get('notes', '')}"
        placed = False
        for key, _title, terms in COLUMNS:
            if _match(text, terms):
                cells[subject][key][date].append(fact_id)
                placed = True
        if placed:
            counts[subject] += 1
    subjects = [("company", company_name or "The company")] + [(item["slug"], item["name"]) for item in competitors]
    lines = [
        "# Competitor matrix draft",
        "",
        f"Built by script on {utc_now()[:10]} from `02-facts/` and `tools/outputs/competitors.json`. "
        "Each cell lists the fact IDs that bear on the column, grouped by source date (`undated` when the fact has none). "
        "A fact can sit in more than one column. The script writes no scores: the competitors writer defines the rubric "
        "below, scores each cell from these facts, and labels every ahead, level, or behind judgment `My inference:`.",
        "",
        "## Evidence base",
        "",
        "| row | kind | facts placed |",
        "|---|---|---:|",
    ]
    kinds = {item["slug"]: item.get("kind", "") for item in competitors}
    for slug, name in subjects:
        lines.append(f"| {name} | {'company' if slug == 'company' else kinds.get(slug, '')} | {counts.get(slug, 0)} |")
    lines += [
        "",
        "A row with far fewer placed facts than the company's is thinner evidence, not a weaker company. "
        "Say so in the competitors file and treat small score gaps as noise.",
        "",
        "## Columns and rubric template",
        "",
        "| column | criteria (a to e, one point each when a P or S fact shows it) |",
        "|---|---|",
    ]
    for _key, title, _terms in COLUMNS:
        lines.append(f"| {title} | {RUBRIC_TEMPLATE[title]} |")
    lines += ["", "Adjust the criteria to the category before scoring, and state the final rubric in the competitors file.", ""]
    for slug, name in subjects:
        lines += [f"## {name}", "", "| column | fact IDs by source date |", "|---|---|"]
        for key, title, _terms in COLUMNS:
            groups = cells.get(slug, {}).get(key, {})
            if not groups:
                lines.append(f"| {title} | none found |")
                continue
            ordered = sorted(groups.items(), key=lambda item: (item[0] == "undated", item[0]), reverse=True)
            ordered = [item for item in ordered if item[0] != "undated"] + [item for item in ordered if item[0] == "undated"]
            text = "; ".join(f"{date}: {', '.join(sorted(set(ids)))}" for date, ids in ordered)
            lines.append(f"| {title} | {text} |")
        if slug != "company" and about_company.get(slug):
            lines += ["", f"How {name} describes the company: {', '.join(sorted(set(about_company[slug])))}"]
        lines.append("")
    if not competitors:
        lines += ["No competitors are registered. The market worker records them with `discovery competitor`.", ""]
    atomic_write_text(root / MATRIX_DRAFT, "\n".join(lines).rstrip() + "\n")
    result = {
        "schema_version": "1.0.0",
        "built_at": utc_now(),
        "rows": [{"slug": slug, "name": name, "facts_placed": counts.get(slug, 0)} for slug, name in subjects],
        "columns": [title for _key, title, _terms in COLUMNS],
        "cells": {slug: {key: dict(groups) for key, groups in columns.items()} for slug, columns in cells.items()},
        "describes_company": dict(about_company),
        "draft": MATRIX_DRAFT,
    }
    atomic_write_json(root / MATRIX_JSON, result)
    return result
