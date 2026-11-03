from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from research_control.competitor_matrix import MATRIX_DRAFT, build_matrix
from research_control.competitors import COMPETITORS_FILE, load_competitors, register_competitor, register_none, subject_metadata
from research_control.discovery import DISCOVERY_CHANNELS, DiscoveryEngine, channel_tried, classify_channel, coverage_markdown
from research_control.io import atomic_write_text
from research_control.runtime import RuntimeStore

SOURCE_ROOT = Path(__file__).resolve().parents[2]

FACTS = """# Q7 competitors

| Fact ID | Claim | Verbatim quote | Source ID | Location | Source date | Grade | Topics | About | Said by | Verdict | Candidate | Notes | Conflict group | Cross-source repeats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CMP-001 | Acme lists a Pro plan at $99 per month | "Pro: $99/month" | SRC-A1 | pricing | 2026-09-01 | P | pricing | Acme | Acme | confirmed | CAND-1 | | | |
| CMP-002 | Acme offers a REST API | "REST API" | SRC-A2 | docs | 2026-08-01 | P | api | Acme | Acme | confirmed | CAND-2 | | | |
| CMP-003 | Acme says Example Co is slower | "slower than Acme" | SRC-A3 | compare | 2026-07-01 | P | positioning | Example Co (per Acme) | Acme | confirmed | CAND-3 | | | |
| CMP-004 | Example Co names Globex as a customer | "Globex uses Example" | SRC-E1 | customers | 2026-06-01 | P | customers | Example Co | Example Co | confirmed | CAND-4 | | | |
| CMP-005 | The market is forecast to grow | "forecast to grow 30%" | SRC-M1 | report | 2026-05-01 | T | market | Market | Gartner (per CIO Dive) | confirmed | CAND-5 | | | |
"""


class CompetitorTests(unittest.TestCase):
    def _engine(self, root: Path):
        shutil.copy2(SOURCE_ROOT / "WORKFLOW.yaml", root / "WORKFLOW.yaml")
        store = RuntimeStore(root)
        store.initialize(run_id="competitors-1", company_url="https://example.com")
        engine = DiscoveryEngine(root, store)
        engine.initialize()
        return store, engine

    def test_new_channels_exist_and_classify(self):
        for channel in ("investors", "people", "archives", "market_competitors"):
            self.assertIn(channel, DISCOVERY_CHANNELS)
        self.assertEqual(classify_channel("https://web.archive.org/web/20250101000000id_/https://example.com/", "example.com"), "archives")
        self.assertEqual(classify_channel("https://www.sec.gov/cgi-bin/browse-edgar?company=example", "example.com"), "investors")
        self.assertEqual(classify_channel("https://example.com/investors/", "example.com"), "investors")
        self.assertEqual(classify_channel("https://example.com/about/leadership", "example.com"), "people")
        self.assertEqual(classify_channel("https://example.com/dashboard", "example.com"), "company_site")

    def test_registered_competitor_tags_sources_and_fills_the_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, engine = self._engine(root)
            with store:
                with self.assertRaises(ValueError):
                    subject_metadata(root, "acme")
                record = register_competitor(root, name="Acme", url="https://acme.example", kind="direct",
                                             reason="same offering to the same buyers", task_id="capture.discover.market-competitors")
                self.assertEqual(record["slug"], "acme")
                self.assertTrue((root / COMPETITORS_FILE).is_file())
                register_competitor(root, name="Acme", url="https://acme.example/", kind="adjacent", reason="revised")
                self.assertEqual([item["kind"] for item in load_competitors(root)], ["adjacent"])
                with self.assertRaises(ValueError):
                    register_none(root, evidence="nothing found")
                result = engine.add_candidates("market_competitors", ["https://acme.example/pricing"], discovered_from="test",
                                               evidence="pricing page", subject="acme")
                source = store.source(result["new_source_ids"][0])
                self.assertEqual(source["metadata"]["subject"], "acme")
                self.assertEqual(source["metadata"]["subject_name"], "Acme")
                again = engine.add_candidates("market_competitors", ["https://acme.example/pricing"], discovered_from="test",
                                              evidence="same page again", subject="acme")
                self.assertEqual(again["new_source_ids"], [])
            (root / "02-facts").mkdir()
            atomic_write_text(root / "02-facts/q07-competitors.md", FACTS)
            result = build_matrix(root, company_name="Example Co")
            draft = (root / MATRIX_DRAFT).read_text(encoding="utf-8")
            self.assertIn("## Acme", draft)
            self.assertIn("CMP-001", draft)
            self.assertIn("2026-09-01: CMP-001", draft)
            self.assertIn("How Acme describes the company: CMP-003", draft)
            self.assertIn("## Example Co", draft)
            self.assertNotIn("CMP-005", draft)
            self.assertEqual(result["rows"][1]["slug"], "acme")
            self.assertGreater(result["rows"][1]["facts_placed"], 0)

    def test_market_channel_needs_registry_before_closing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, engine = self._engine(root)
            with store:
                engine.add_candidates("market_competitors", ["https://rival.example/"], discovered_from="t", evidence="Q7 search")
                with self.assertRaises(ValueError):
                    engine.close_channel("market_competitors", "sufficient", "Q7: covered by rival pages")
                register_none(root, evidence="searched comparison pages and directories; none")
                closed = engine.close_channel("market_competitors", "sufficient", "Q7: covered by rival pages")
                self.assertEqual(closed["state"], "sufficient")

    def test_blocked_close_and_none_alternate_require_two_approaches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, engine = self._engine(root)
            with store:
                with self.assertRaises(ValueError):
                    engine.close_channel("social", "blocked", "login wall")
                with self.assertRaises(ValueError):
                    engine.close_channel("social", "blocked", "login wall", tried=["direct -> login wall", "direct -> login wall"])
                closed = engine.close_channel("social", "blocked", "login wall everywhere",
                                              tried=["direct fetch -> login wall", "Wayback -> no captures"])
                self.assertEqual(closed["state"], "blocked")
                self.assertEqual(len(channel_tried(store.discovery_channel("social"))), 2)
                coverage = coverage_markdown(store.discovery_channels())
                self.assertIn("Approaches tried", coverage)
                self.assertIn("Wayback -> no captures", coverage)
                result = engine.add_candidates("independent_web", ["https://news.example.org/story"], discovered_from="t", evidence="q")
                source_id = result["new_source_ids"][0]
                with self.assertRaises(ValueError):
                    engine.add_alternate(source_id, None, "searched wires and archives")
                row = engine.add_alternate(source_id, None, "searched wires and archives",
                                           tried=["PR Newswire search -> none", "Wayback -> no snapshot"])
                self.assertEqual(row["outcome"], "none_found")
                self.assertEqual(len(row["tried"]), 2)
                with_url = engine.add_alternate(source_id, "https://wire.example/story", "wire copy")
                self.assertEqual(with_url["outcome"], "admitted")


if __name__ == "__main__":
    unittest.main()
