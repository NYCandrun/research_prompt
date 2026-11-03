"""Start runs from one or more domains: one company, or one run per company.

`start --url A --url B` gathers what each homepage says about itself (title,
description, site name, copyright line, links between the given domains, a
short excerpt) into one brief, and a worker on the standard tier decides which
domains belong to one company. `start --apply ID` checks that decision and
provisions one run per company, with every extra domain of a company as a
first-party domain of its run. With one URL there is nothing to decide and the
run starts at once. Grouping files live under `runs/_grouping/<id>/`, outside
the template's git like every run.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from research_control.capture import TextExtractor
from research_control.discovery import (
    DiscoveryPolicy,
    FetchResult,
    LinkExtractor,
    _same_company_host,
    canonicalize_url,
    host_key,
    public_fetch,
)
from research_control.io import atomic_write_json, atomic_write_text, load_json, utc_now
from research_control.orchestration import validate_url
from research_control.provision import RUNS_DIRECTORY, provision_run, run_slug
from research_control.tooling import record_setup

GROUPING_DIRECTORY = f"{RUNS_DIRECTORY}/_grouping"
EVIDENCE_FILE = "evidence.json"
BRIEF_FILE = "brief.md"
DECISION_FILE = "decision.json"
APPLIED_FILE = "applied.json"
EXCERPT_CHARS = 1_500
CONFIDENCE = {"clear", "unsure"}
Fetcher = Callable[[str, DiscoveryPolicy], FetchResult]


def normalize_url(value: str) -> str:
    """Accept a bare domain ("ideo.com") as well as a full URL."""
    value = value.strip()
    if value and "://" not in value:
        value = f"https://{value}"
    if not re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?(/\S*)?", value):
        raise ValueError(f"not a domain or URL: {value!r}")
    return validate_url(value)


def grouping_id(urls: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(host_key(url) for url in urls)).encode("utf-8")).hexdigest()
    return f"g-{digest[:8]}"


def grouping_root(template_root: Path, identifier: str) -> Path:
    return template_root / GROUPING_DIRECTORY / identifier


def _clip(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def gather_evidence(url: str, others: list[str], fetcher: Fetcher) -> dict[str, Any]:
    """What one homepage says about itself, and whether it points at the other domains."""
    host = host_key(url)
    record: dict[str, Any] = {"url": url, "host": host}
    try:
        result = fetcher(url, DiscoveryPolicy())
    except Exception as error:  # the worker still decides; it just knows this page was not readable
        record["status"] = _clip(f"unavailable: {type(error).__name__}: {error}", 300)
        return record
    body = result.body.decode("utf-8", errors="replace")
    text_parser = TextExtractor()
    text_parser.feed(body)
    links = LinkExtractor()
    links.feed(body)
    text = text_parser.text()
    meta = text_parser.meta
    absolute: list[tuple[str, str]] = []
    for href, anchor in links.links:
        try:
            absolute.append((canonicalize_url(href, result.url), anchor))
        except ValueError:
            continue
    record.update({
        "status": "fetched",
        "final_url": result.url,
        "title": _clip(text_parser.title(), 200),
        "description": _clip(meta.get("description") or meta.get("og:description") or "", 300),
        "site_name": _clip(meta.get("og:site_name") or "", 120),
        "canonical": links.canonical or "",
        "copyright_lines": [
            _clip(line, 160) for line in text.splitlines() if re.search(r"©|\(c\)|copyright", line, re.IGNORECASE)
        ][:3],
        "links_to_other_domains": {
            host_key(other): [
                {"url": link, "text": _clip(anchor, 80)} for link, anchor in absolute if _same_company_host(link, host_key(other))
            ][:5]
            for other in others
        },
        "about_links": [
            {"url": link, "text": _clip(anchor, 80)} for link, anchor in absolute
            if "about" in link.casefold() or "about" in anchor.casefold()
        ][:5],
        "excerpt": _clip(text, EXCERPT_CHARS),
    })
    return record


def write_brief(directory: Path, urls: list[str], evidence: list[dict[str, Any]]) -> Path:
    lines = [
        "# Are these domains one company?",
        "",
        "You decide which of the domains below belong to one company, so the research can run as one run",
        "per company. The homepages were already read for you; what each says about itself is below. Decide",
        "from that. Open a page yourself only when the evidence is not enough: the homepage, an about or",
        "company page, a footer, a legal or privacy page, on any of these domains, public pages only. Off",
        "limits: no logins or accounts, no payment or paywall-removal tricks, no path a site's robots.txt",
        "disallows.",
        "",
        "## What counts as one company",
        "",
        "One company: the same organization under another address, such as a learning arm (IDEO and IDEO U),",
        "a product brand, a regional or language site, or a unit the company presents on its own pages as its",
        "own. Signs: the same legal name in the copyright line, links between the sites that call the other",
        "\"our\" something, the same leadership, one about page that covers both.",
        "",
        "Separate companies: distinct organizations, even when related. A parent and a subsidiary with its",
        "own name, leadership, and products; an investor and a company it funds; a partner; a customer; a",
        "company and its former owner. When the evidence is split, keep them separate, say why, and set",
        "`confidence` to `unsure` with the one question that would settle it.",
        "",
        "## Domains",
        "",
    ]
    for record in evidence:
        lines += [f"### {record['host']}", "", f"URL given: {record['url']}", ""]
        if record.get("status") != "fetched":
            lines += [f"The homepage could not be read: {record.get('status', 'unavailable')}.", ""]
            continue
        lines += [
            f"- Final URL: {record['final_url']}",
            f"- Title: {record['title'] or '(none)'}",
            f"- Description: {record['description'] or '(none)'}",
            f"- Site name: {record['site_name'] or '(none)'}",
            f"- Copyright: {'; '.join(record['copyright_lines']) or '(no copyright line found)'}",
        ]
        for other, found in record["links_to_other_domains"].items():
            if found:
                shown = ", ".join(f"{item['text'] or item['url']}" for item in found)
                lines.append(f"- Links to {other}: {shown}")
            else:
                lines.append(f"- Links to {other}: none on the homepage")
        if record["about_links"]:
            lines.append("- About pages: " + ", ".join(item["url"] for item in record["about_links"]))
        lines += ["", "Homepage text (start):", "", "> " + record["excerpt"].replace("\n", " "), ""]
    decision_path = directory / DECISION_FILE
    lines += [
        "## What to write",
        "",
        f"Write `{decision_path}` as JSON in this shape, American English throughout:",
        "",
        "```json",
        json.dumps({
            "groups": [
                {"name": "Company name", "urls": ["main site URL first", "each other domain of the same company"],
                 "reason": "one or two sentences naming the evidence"},
            ],
            "confidence": "clear or unsure",
            "question": "empty when clear; when unsure, the one question for the user, with your recommendation",
        }, indent=2),
        "```",
        "",
        "Rules: every domain given above appears in exactly one group, written as given; the first URL in a",
        "group is the company's main site; `name` is the company's name as it writes it. Then run",
        f"`python3 -m research_control start --validate {directory.name}` from the repository root and fix",
        "anything it reports. Report back in two lines: the groups you made and the reason.",
        "",
    ]
    path = directory / BRIEF_FILE
    atomic_write_text(path, "\n".join(lines))
    return path


def _one_domain(urls: list[str]) -> bool:
    """One URL, or several addresses on one domain (www.ideo.com and designkit.ideo.com): nothing to decide."""
    hosts = [host_key(url) for url in urls]
    shortest = min(hosts, key=len)
    return all(_same_company_host(url, shortest) for url in urls)


def start_runs(template_root: Path, urls: list[str], fetcher: Fetcher | None = None) -> dict[str, Any]:
    """One URL starts its run; several write the grouping brief for a worker."""
    normalized = list(dict.fromkeys(normalize_url(value) for value in urls))
    if not normalized:
        raise ValueError("pass at least one --url")
    if _one_domain(normalized):
        return {"status": "started", "runs": [_provision(template_root, normalized[0], normalized[1:])]}
    identifier = grouping_id(normalized)
    directory = grouping_root(template_root, identifier)
    if (directory / DECISION_FILE).is_file():
        return {
            "status": "decided", "grouping_id": identifier,
            "next": f"python3 -m research_control start --apply {identifier}",
        }
    fetch = fetcher or public_fetch
    evidence = [gather_evidence(url, [other for other in normalized if other != url], fetch) for url in normalized]
    atomic_write_json(directory / EVIDENCE_FILE, {"urls": normalized, "gathered_at": utc_now(), "domains": evidence})
    brief = write_brief(directory, normalized, evidence)
    return {
        "status": "decide",
        "grouping_id": identifier,
        "urls": normalized,
        "start_workers": [{"tasks": ["group-domains"], "model_level": "standard", "effort": "medium", "read": str(brief)}],
        "next": f"python3 -m research_control start --apply {identifier}",
    }


def validate_decision(template_root: Path, identifier: str) -> dict[str, Any]:
    directory = grouping_root(template_root, identifier)
    errors: list[str] = []
    if not (directory / EVIDENCE_FILE).is_file():
        return {"ok": False, "errors": [f"no grouping {identifier}; run `start --url ...` first"], "groups": []}
    given = [str(item) for item in load_json(directory / EVIDENCE_FILE)["urls"]]
    given_hosts = {host_key(url): url for url in given}
    path = directory / DECISION_FILE
    if not path.is_file():
        return {"ok": False, "errors": [f"{DECISION_FILE} is missing"], "groups": []}
    try:
        decision = load_json(path)
    except Exception as error:
        return {"ok": False, "errors": [f"{DECISION_FILE} is not valid JSON: {error}"], "groups": []}
    groups = decision.get("groups") if isinstance(decision, dict) else None
    if not isinstance(groups, list) or not groups:
        return {"ok": False, "errors": ["`groups` must be a non-empty list"], "groups": []}
    seen: dict[str, int] = {}
    cleaned: list[dict[str, Any]] = []
    texts: list[str] = []
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            errors.append(f"group {index} is not an object")
            continue
        name = str(group.get("name") or "").strip()
        reason = str(group.get("reason") or "").strip()
        urls = group.get("urls")
        if not name:
            errors.append(f"group {index} has no `name`")
        if not reason:
            errors.append(f"group {index} has no `reason`")
        if not isinstance(urls, list) or not urls:
            errors.append(f"group {index} has no `urls`")
            continue
        resolved: list[str] = []
        for value in urls:
            host = host_key(str(value)) if "://" in str(value) else host_key(f"https://{value}")
            if host not in given_hosts:
                errors.append(f"group {index}: {value} was not one of the domains given")
                continue
            seen[host] = seen.get(host, 0) + 1
            resolved.append(given_hosts[host])
        texts += [name, reason]
        cleaned.append({"name": name, "urls": resolved, "reason": reason})
    for host, url in given_hosts.items():
        count = seen.get(host, 0)
        if count == 0:
            errors.append(f"{url} is in no group")
        elif count > 1:
            errors.append(f"{url} is in {count} groups")
    confidence = str(decision.get("confidence") or "").strip()
    question = str(decision.get("question") or "").strip()
    if confidence not in CONFIDENCE:
        errors.append("`confidence` must be `clear` or `unsure`")
    if confidence == "unsure" and not question:
        errors.append("`question` is required when `confidence` is `unsure`")
    texts.append(question)
    from research_control.validators import american

    errors += [f'"{word}" (use {advice})' for text in texts for word, advice in american.findings(text)]
    return {"ok": not errors, "errors": errors, "groups": cleaned, "confidence": confidence, "question": question}


def _provision(template_root: Path, primary: str, also: list[str]) -> dict[str, Any]:
    from research_control.adaptive import advance

    run_root = template_root / RUNS_DIRECTORY / run_slug(primary)
    relative = f"{RUNS_DIRECTORY}/{run_slug(primary)}"
    if (run_root / "tools/outputs/run-state.json").is_file():
        return {
            "status": "exists", "run_root": str(run_root), "company_url": primary, "also": also,
            "next": f"cd {relative} && python3 -m research_control run",
        }
    provision_run(template_root, run_root)
    result = advance(run_root, primary, also_urls=also)
    record_setup(template_root, run_root)
    return {
        "status": "started", "run_root": str(run_root), "company_url": primary, "also": also,
        "advance": result.get("status"), "next": f"cd {relative} && python3 -m research_control run",
    }


def apply_decision(template_root: Path, identifier: str) -> dict[str, Any]:
    """Provision one run per company the worker decided on."""
    checked = validate_decision(template_root, identifier)
    if not checked["ok"]:
        raise ValueError("the decision does not pass: " + "; ".join(checked["errors"]))
    runs = []
    for group in checked["groups"]:
        runs.append({"name": group["name"], **_provision(template_root, group["urls"][0], group["urls"][1:])})
    record = {"applied_at": utc_now(), "confidence": checked["confidence"], "question": checked["question"], "runs": runs}
    atomic_write_json(grouping_root(template_root, identifier) / APPLIED_FILE, record)
    return {"status": "started", "grouping_id": identifier, **record}
