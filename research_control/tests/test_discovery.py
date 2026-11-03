from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from research_control.discovery import DiscoveryEngine, DiscoveryPolicy, FetchResult, canonicalize_url, xml_links
from research_control.runtime import RuntimeStore


SOURCE_ROOT = Path(__file__).resolve().parents[2]


class DiscoveryTests(unittest.TestCase):
    def test_sitemap_and_feed_links_are_extracted(self) -> None:
        body = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>'
        self.assertEqual(["https://example.com/a", "https://example.com/b"], xml_links(body))

    def test_company_frontier_stops_on_saturation_not_source_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(SOURCE_ROOT / "WORKFLOW.yaml", root / "WORKFLOW.yaml")
            graph = {
                "https://example.com/": b'<a href="/about?utm_source=test">About</a><a href="https://youtube.com/@example">Video</a>',
                "https://example.com/about": b"<html><body>About Example</body></html>",
            }

            def fetch(url: str, _policy: DiscoveryPolicy) -> FetchResult:
                return FetchResult(url=url, content_type="text/html", body=graph[url])

            with RuntimeStore(root) as store:
                store.initialize(run_id="discover-1", company_url="https://example.com")
                engine = DiscoveryEngine(root, store, fetcher=fetch)
                engine.initialize()
                first = engine.crawl_company_site()
                self.assertGreater(first["new_sources"], 0)
                self.assertEqual("open", first["status"])
                second = engine.crawl_company_site()
                self.assertEqual("open", second["status"])
                third = engine.crawl_company_site()
                self.assertEqual("saturated", third["status"])
                self.assertEqual(3, len(store.sources()))
                self.assertEqual(
                    "https://example.com/about",
                    canonicalize_url("https://EXAMPLE.com/about/?utm_source=x"),
                )

    def test_external_channel_needs_repeated_empty_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(SOURCE_ROOT / "WORKFLOW.yaml", root / "WORKFLOW.yaml")
            with RuntimeStore(root) as store:
                store.initialize(run_id="discover-2", company_url="https://example.com")
                engine = DiscoveryEngine(root, store)
                engine.initialize()
                with self.assertRaises(ValueError):
                    engine.close_channel("independent_web", "saturated", "unsupported shortcut")
                one = engine.add_candidates(
                    "independent_web", ["https://news.example.org/story"],
                    discovered_from="query-1", evidence="first query family",
                )
                self.assertEqual(1, len(one["new_source_ids"]))
                self.assertEqual("open", one["channel_state"]["state"])
                empty_one = engine.add_candidates(
                    "independent_web", [], discovered_from="query-2", evidence="second query family: no new evidence",
                )
                self.assertEqual("open", empty_one["channel_state"]["state"])
                empty_two = engine.add_candidates(
                    "independent_web", [], discovered_from="query-3", evidence="third query family: no new evidence",
                )
                self.assertEqual("saturated", empty_two["channel_state"]["state"])
                engine.close_channel("video", "incomplete", "fixture safety breaker")
                summary = store.summary()["discovery"]
                self.assertFalse(summary["complete"])
                self.assertIn("video", summary["limitations"])


if __name__ == "__main__":
    unittest.main()


class BlockedRecordTests(unittest.TestCase):
    def _engine(self, root: Path):
        shutil.copy2(SOURCE_ROOT / "WORKFLOW.yaml", root / "WORKFLOW.yaml")
        store = RuntimeStore(root)
        store.initialize(run_id="blocked-1", company_url="https://example.com")
        engine = DiscoveryEngine(root, store)
        engine.initialize()
        return store, engine

    def test_blocked_close_requires_two_distinct_approaches(self) -> None:
        from research_control.discovery import channel_tried
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, engine = self._engine(root)
            with store:
                with self.assertRaises(ValueError):
                    engine.close_channel("social", "blocked", "login wall")
                with self.assertRaises(ValueError):
                    engine.close_channel("social", "blocked", "login wall", tried=["direct fetch -> login wall", "direct fetch -> login wall"])
                engine.close_channel("not_applicable_channel".replace("not_applicable_channel", "podcasts"), "not_applicable", "no podcast exists")
                result = engine.close_channel(
                    "social", "blocked", "login wall on every surface",
                    tried=["direct fetch -> login wall", "Wayback snapshot -> no captures", "company blog copy -> none"],
                )
                self.assertEqual(result["state"], "blocked")
                self.assertEqual(len(channel_tried(store.discovery_channel("social"))), 3)
                coverage = (root / "06-checks/discovery-coverage.md").read_text(encoding="utf-8")
                self.assertIn("Approaches tried", coverage)
                self.assertIn("Wayback snapshot -> no captures", coverage)

    def test_blocked_source_part_writes_receipt_and_needs_approaches(self) -> None:
        from research_control.capture import blocked_source_part
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, engine = self._engine(root)
            with store:
                engine.add_candidates("independent_web", ["https://news.example.org/story"], discovered_from="test", evidence="fixture", record_pass=True)
                source_id = store.sources()[0]["source_id"]
                with self.assertRaises(ValueError):
                    blocked_source_part(root, source_id=source_id, reason="paywall", tried=["direct -> paywall"], store=store)
                receipt = blocked_source_part(
                    root, source_id=source_id, reason="hard paywall",
                    tried=["direct fetch -> paywall", "Wayback -> no snapshot", "syndicated copy -> none found"], store=store,
                )
                self.assertEqual(receipt["status"], "blocked")
                self.assertTrue((root / "01-sources/captures" / source_id / "BLOCKED.txt").is_file())
                self.assertTrue((root / receipt["receipt"]).is_file())
                self.assertEqual(store.source(source_id)["status"], "blocked")
                self.assertEqual(len(store.source(source_id)["metadata"]["tried"]), 3)
