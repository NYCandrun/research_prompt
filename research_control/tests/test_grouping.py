from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_control.discovery import DiscoveryPolicy, FetchResult
from research_control.grouping import (
    DECISION_FILE,
    apply_decision,
    grouping_root,
    normalize_url,
    start_runs,
    validate_decision,
)
from research_control.io import atomic_write_text, load_json
from research_control.provision import provision_run

SOURCE_ROOT = Path(__file__).resolve().parents[2]

PAGES = {
    "https://www.ideo.example": (
        b"<html><head><title>IDEO | Design company</title>"
        b'<meta name="description" content="IDEO is a global design company."></head>'
        b'<body><a href="/about">About IDEO</a><a href="https://www.ideou.example/">IDEO U, our learning arm</a>'
        b"<footer>\xc2\xa9 2026 IDEO LP. All rights reserved.</footer></body></html>"
    ),
    "https://www.ideou.example": (
        b"<html><head><title>IDEO U: Online courses</title></head>"
        b'<body><a href="https://www.ideo.example/">From IDEO</a><footer>\xc2\xa9 2026 IDEO LP</footer></body></html>'
    ),
    "https://acme.example": b"<html><head><title>Acme</title></head><body>Acme sells workflow software.</body></html>",
}


def fetch(url: str, _policy: DiscoveryPolicy) -> FetchResult:
    if url not in PAGES:
        raise ValueError("unreadable")
    return FetchResult(url=url + "/", content_type="text/html", body=PAGES[url])


def _template(directory: str) -> Path:
    template = Path(directory) / "template"
    provision_run(SOURCE_ROOT, template)
    return template


class GroupingTests(unittest.TestCase):
    def test_one_domain_starts_its_run_at_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = _template(directory)
            result = start_runs(template, ["acme.example"], fetcher=fetch)
            self.assertEqual(result["status"], "started")
            run = result["runs"][0]
            self.assertEqual(run["company_url"], "https://acme.example")
            self.assertTrue((Path(run["run_root"]) / "tools/outputs/run-state.json").is_file())
            self.assertEqual(run["next"], "cd runs/acme-example && python3 -m research_control run")
            again = start_runs(template, ["https://acme.example", "https://docs.acme.example"], fetcher=fetch)
            self.assertEqual(again["runs"][0]["status"], "exists")

    def test_several_domains_write_a_brief_and_a_checked_decision_starts_the_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = _template(directory)
            urls = ["https://www.ideo.example", "ideou.example", "https://acme.example", "https://dark.example"]
            result = start_runs(template, urls, fetcher=fetch)
            self.assertEqual(result["status"], "decide")
            self.assertEqual(result["start_workers"][0]["model_level"], "standard")
            brief = Path(result["start_workers"][0]["read"]).read_text(encoding="utf-8")
            self.assertIn("IDEO U, our learning arm", brief)
            self.assertIn("© 2026 IDEO LP", brief)
            self.assertIn("Links to ideou.example: none on the homepage", brief)
            self.assertIn("The homepage could not be read", brief)
            self.assertIn("no logins or accounts", brief)
            identifier = result["grouping_id"]
            self.assertEqual(start_runs(template, urls, fetcher=fetch)["grouping_id"], identifier)

            directory_path = grouping_root(template, identifier)
            atomic_write_text(directory_path / DECISION_FILE, json.dumps({
                "groups": [{"name": "IDEO", "urls": ["https://www.ideo.example"], "reason": "x"}],
                "confidence": "maybe",
            }))
            checked = validate_decision(template, identifier)
            self.assertFalse(checked["ok"])
            self.assertIn("https://ideou.example is in no group", checked["errors"])
            self.assertIn("`confidence` must be `clear` or `unsure`", checked["errors"])
            with self.assertRaises(ValueError):
                apply_decision(template, identifier)

            atomic_write_text(directory_path / DECISION_FILE, json.dumps({
                "groups": [
                    {"name": "IDEO", "urls": ["https://www.ideo.example", "https://ideou.example"],
                     "reason": "IDEO U calls itself IDEO's learning arm and both carry the IDEO LP copyright line."},
                    {"name": "Acme", "urls": ["https://acme.example"], "reason": "A separate company; no link either way."},
                    {"name": "Dark", "urls": ["https://dark.example"], "reason": "Unreadable homepage, no link from the others."},
                ],
                "confidence": "unsure",
                "question": "Is dark.example part of Acme? I recommend separate runs.",
            }))
            checked = validate_decision(template, identifier)
            self.assertTrue(checked["ok"], checked["errors"])
            applied = apply_decision(template, identifier)
            self.assertEqual([run["name"] for run in applied["runs"]], ["IDEO", "Acme", "Dark"])
            ideo = applied["runs"][0]
            state = load_json(Path(ideo["run_root"]) / "tools/outputs/run-state.json")
            self.assertEqual(state["company_hosts"], ["ideo.example", "ideou.example"])
            self.assertEqual(applied["question"], "Is dark.example part of Acme? I recommend separate runs.")
            self.assertTrue((template / "runs/acme-example/tools/outputs/run-state.json").is_file())
            self.assertEqual(start_runs(template, urls, fetcher=fetch)["status"], "decided")

    def test_bare_domains_and_british_spelling(self) -> None:
        self.assertEqual(normalize_url(" ideo.com "), "https://ideo.com")
        with self.assertRaises(ValueError):
            normalize_url("not a url")
        with tempfile.TemporaryDirectory() as directory:
            template = _template(directory)
            result = start_runs(template, ["https://www.ideo.example", "https://acme.example"], fetcher=fetch)
            atomic_write_text(grouping_root(template, result["grouping_id"]) / DECISION_FILE, json.dumps({
                "groups": [
                    {"name": "IDEO", "urls": ["https://www.ideo.example"], "reason": "A design organisation."},
                    {"name": "Acme", "urls": ["https://acme.example"], "reason": "Separate."},
                ],
                "confidence": "clear", "question": "",
            }))
            checked = validate_decision(template, result["grouping_id"])
            self.assertFalse(checked["ok"])
            self.assertTrue(any("organisation" in error for error in checked["errors"]), checked["errors"])


if __name__ == "__main__":
    unittest.main()
