from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from research_control.checks import _validate_scope
from research_control.discovery import DiscoveryEngine, DiscoveryPolicy, FetchResult, _same_company_host, classify_channel
from research_control.io import atomic_write_text
from research_control.orchestration import add_first_party_host, first_party, initialize
from research_control.provision import provision_run
from research_control.runtime import RuntimeStore

SOURCE_ROOT = Path(__file__).resolve().parents[2]


class FirstPartyTests(unittest.TestCase):
    def test_host_checks_accept_every_first_party_domain(self):
        hosts = ["ideo.com", "ideou.com"]
        self.assertTrue(_same_company_host("https://www.ideou.com/courses", hosts))
        self.assertTrue(_same_company_host("https://designkit.ideo.com/", hosts))
        self.assertFalse(_same_company_host("https://www.ideo-rivals.com/", hosts))
        self.assertEqual(classify_channel("https://www.ideou.com/pages/about", hosts), "company_site")
        self.assertEqual(classify_channel("https://www.ideou.com/blog/design-thinking", hosts), "newsroom_blog")
        self.assertEqual(classify_channel("https://www.ideou.com/pages/about", "ideo.com"), "independent_web")

    def test_run_state_keeps_the_domains_and_scope_check_accepts_either(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            provision_run(SOURCE_ROOT, root)
            state = initialize(root, "https://www.ideo.com", also_urls=["https://www.ideou.com"])
            self.assertEqual(state["company_hosts"], ["ideo.com", "ideou.com"])
            self.assertEqual(first_party(root), (["https://www.ideo.com", "https://www.ideou.com"], ["ideo.com", "ideou.com"]))
            atomic_write_text(root / "00-scope.md", "# Scope\n\nCompany: ideou.com\n\n## Inputs\n## Source plan\n## Competitors\n\n**Q1. Product**\n")
            self.assertEqual(_validate_scope(root)["status"], "PASS")
            added = add_first_party_host(root, "https://labs.ideo.example", "named in the footer as an IDEO company")
            self.assertTrue(added["added"])
            self.assertEqual(first_party(root)[1], ["ideo.com", "ideou.com", "labs.ideo.example"])
            self.assertFalse(add_first_party_host(root, "https://www.ideou.com/", "again")["added"])
            self.assertIn("first-party-host-added", (root / "RUN_HISTORY.md").read_text(encoding="utf-8"))

    def test_crawl_covers_every_first_party_domain_as_the_companys_own(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            provision_run(SOURCE_ROOT, root)
            initialize(root, "https://ideo.example", also_urls=["https://ideou.example"])
            graph = {
                "https://ideo.example/": b'<a href="/about">About</a><a href="https://ideou.example/">IDEO U</a>',
                "https://ideo.example/about": b"<html><body>About IDEO</body></html>",
                "https://ideou.example/": b'<a href="/courses/design-thinking">Course</a>',
                "https://ideou.example/courses/design-thinking": b"<html><body>A course</body></html>",
            }

            def fetch(url: str, _policy: DiscoveryPolicy) -> FetchResult:
                if url.endswith("/robots.txt") or url.endswith("/sitemap.xml"):
                    raise ValueError("none")
                return FetchResult(url=url, content_type="text/html", body=graph[url])

            with RuntimeStore(root) as store:
                store.initialize(run_id="ideo-1", company_url="https://ideo.example")
                engine = DiscoveryEngine(root, store, fetcher=fetch)
                engine.initialize()
                self.assertEqual(engine.company_hosts, ["ideo.example", "ideou.example"])
                seeds = {source["canonical_url"] for source in store.sources() if source.get("metadata", {}).get("seed")}
                self.assertEqual(seeds, {"https://ideo.example/", "https://ideou.example/"})
                while engine.crawl_company_site()["status"] == "open":
                    pass
                by_url = {source["canonical_url"]: source for source in store.sources()}
                self.assertIn("https://ideou.example/courses/design-thinking", by_url)
                self.assertEqual(by_url["https://ideou.example/courses/design-thinking"]["channel"], "company_site")
                self.assertEqual(by_url["https://ideo.example/about"]["channel"], "company_site")


if __name__ == "__main__":
    unittest.main()
