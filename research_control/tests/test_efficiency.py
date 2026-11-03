from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_control.adaptive import advance
from research_control.citation_tables import TABLES, build_review_tables
from research_control.dispatch import _prompt, task_material, write_packet
from research_control.io import atomic_write_json, atomic_write_text
from research_control.orchestration import initialize
from research_control.provision import provision_run
from research_control.runtime import RuntimeStore

SOURCE_ROOT = Path(__file__).resolve().parents[2]

FACTS = """# Q1 product

| Fact ID | Claim | Verbatim quote | Source ID | Location | Source date | Grade | Topics | About | Said by | Verdict | Candidate | Notes | Conflict group | Cross-source repeats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRD-001 | Acme sells workflow software | "workflow software for operations teams" | SRC-1 | homepage | 2026-09-01 | P | product | Acme | Acme | confirmed | CAND-1 | | | |
| PRD-002 | Acme lists a Pro plan | "Pro plan" | SRC-2 | pricing | 2026-08-01 | P | pricing | Acme | Acme | confirmed | CAND-2 | | | |
| PRD-003 | Acme names Globex as a customer | "Globex uses Acme" | SRC-3 | customers | 2026-07-01 | P | customers | Acme | Acme | confirmed | CAND-3 | | | |
"""


def citation_map() -> dict:
    return {
        "document": "05-synthesis/company-brief.md",
        "sources": {"SRC-1": {"url": "https://acme.example/"}, "SRC-2": {"url": "https://acme.example/pricing"}, "SRC-3": {"url": "https://acme.example/customers"}},
        "facts": {"PRD-001": {"source_ids": ["SRC-1"]}, "PRD-002": {"source_ids": ["SRC-2"]}, "PRD-003": {"source_ids": ["SRC-3"]}},
        "notes": [
            {"n": 1, "source_id": "SRC-1", "url": "https://acme.example/", "publisher": "Acme", "date": "2026-09-01", "grade": "P"},
            {"n": 2, "source_id": "SRC-2", "url": "https://acme.example/pricing", "publisher": "Acme", "date": "2026-08-01", "grade": "P"},
            {"n": 3, "source_id": "SRC-3", "url": "https://acme.example/customers", "publisher": "Acme", "date": "2026-07-01", "grade": "P"},
        ],
        "citations": [
            {"n": 1, "facts": ["PRD-001"], "place": "Acme sells workflow software", "link": "https://acme.example/#:~:text=workflow"},
            {"n": 2, "facts": ["PRD-002"], "place": "a Pro plan", "link": "https://acme.example/pricing#:~:text=Pro"},
            {"n": 3, "facts": ["PRD-003"], "place": "Globex is a customer", "link": "https://acme.example/customers#:~:text=Globex"},
            {"n": 1, "facts": ["PRD-001"], "place": "software for operations teams", "link": "https://acme.example/#:~:text=workflow"},
        ],
        "markdown_citations": [{"n": 1, "facts": ["PRD-001"]}, {"n": 2, "facts": ["PRD-002"]}, {"n": 3, "facts": ["PRD-003"]}, {"n": 1, "facts": ["PRD-001"]}],
    }


class EfficiencyTests(unittest.TestCase):
    def test_review_tables_split_citations_and_index_facts_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_write_text(root / "02-facts/q01-product.md", FACTS)
            atomic_write_json(root / "tools/outputs/citation-map-company-brief.json", citation_map())
            result = build_review_tables(root)
            self.assertEqual(result["citations"], 4)
            self.assertEqual((result["a"]["citations"], result["b"]["citations"]), (2, 2))
            a = (root / TABLES["a"]).read_text(encoding="utf-8")
            b = (root / TABLES["b"]).read_text(encoding="utf-8")
            self.assertIn("### 1. citation 1", a)
            self.assertIn("before it: Acme sells workflow software", a)
            self.assertIn("### PRD-002", a)
            self.assertNotIn("### PRD-003", a)
            self.assertIn("### PRD-003", b)
            self.assertIn('quote: "Globex uses Acme"', b)
            self.assertEqual(b.count("### PRD-001"), 1)

    def test_inputs_marked_not_inline_are_listed_not_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_write_text(root / "big.json", "{}" * 1000)
            atomic_write_text(root / "small.md", "hello")
            task = {"inputs": [{"id": "map", "path": "big.json", "inline": False}, {"id": "text", "path": "small.md"}], "outputs": []}
            material, elsewhere, fingerprints = task_material(root, task)
            self.assertIn("big.json", elsewhere)
            self.assertIn("=== FILE: small.md ===", material)
            self.assertNotIn("big.json", fingerprints)

    def test_prompt_sections_filter_by_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_write_text(root / "p.md", "# T\n\nintro\n\n## A\n<!-- only: careers -->\nA body\n\n## B\n<!-- only: market_competitors, code_packages -->\nB body\n\n## C\n\nC body\n")
            careers = _prompt(root, "p.md", "source_discovery", ["careers"])
            self.assertIn("A body", careers)
            self.assertNotIn("B body", careers)
            self.assertIn("C body", careers)
            market = _prompt(root, "p.md", "source_discovery", ["market_competitors"])
            self.assertIn("B body", market)
            self.assertNotIn("A body", market)
            self.assertIn("A body", _prompt(root, "p.md", None))

    def test_discovery_brief_carries_only_its_channel_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            provision_run(SOURCE_ROOT, root)
            initialize(root, "https://acme.example")
            base = {
                "phase": "capture", "task_type": "source_discovery", "attempt_count": 0, "state": "ready", "independent": True,
                "exclusive_inputs": False, "output_mode": "create", "track_input_staleness": False, "host_key": "",
                "outputs": ["out/x.json"], "depends_on": [], "schema_files": [], "validators": [],
                "prompt_files": ["prompts/core/runtime.md", "prompts/core/evidence.md", "prompts/phases/discovery.md"],
            }
            careers = write_packet(root, {**base, "task_id": "capture.discover.careers",
                                           "inputs": [{"id": "channels", "value": ["careers"]}], "metadata": {"channels": ["careers"]}})
            market = write_packet(root, {**base, "task_id": "capture.discover.market-competitors",
                                          "inputs": [{"id": "channels", "value": ["market_competitors"]}], "metadata": {"channels": ["market_competitors"]}})
            careers_text = (root / careers["packet"]).read_text(encoding="utf-8")
            market_text = (root / market["packet"]).read_text(encoding="utf-8")
            self.assertNotIn("## Competitors and the market", careers_text)
            self.assertNotIn("## Public code", careers_text)
            self.assertIn("## Closing the channel", careers_text)
            self.assertIn("## Competitors and the market", market_text)
            self.assertIn("## Finding GitHub organizations", market_text)
            self.assertLess(len(careers_text), len(market_text) - 10_000)

    def test_work_start_claims_an_unclaimed_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            provision_run(SOURCE_ROOT, root)
            advance(root, "https://acme.example", automatic=False)
            with RuntimeStore(root) as store:
                self.assertEqual(store.task("scope.scope")["state"], "ready")
            completed = subprocess.run(
                [sys.executable, "-m", "research_control", "work", "start", "scope.scope", "--worker-id", "w-scope"],
                cwd=root, text=True, capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["state"], "running")


if __name__ == "__main__":
    unittest.main()
