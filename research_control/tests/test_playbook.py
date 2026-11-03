from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research_control.dispatch import write_packet
from research_control.playbook import MIN_TRIED, distinct_tried, load_sections, playbook_for_task, require_tried, section_keys, sections

SOURCE_ROOT = Path(__file__).resolve().parents[2]


def task(task_type: str, **overrides) -> dict:
    base = {
        "task_id": f"capture.{task_type}.x", "phase": "capture", "task_type": task_type, "attempt_count": 0,
        "state": "ready", "independent": True, "exclusive_inputs": True, "output_mode": "create",
        "track_input_staleness": False, "host_key": "", "inputs": [], "outputs": ["out/x.json"], "depends_on": [],
        "prompt_files": ["prompts/core/runtime.md"], "schema_files": [], "validators": [], "metadata": {},
    }
    base.update(overrides)
    return base


class PlaybookTests(unittest.TestCase):
    def test_real_playbook_parses_with_channel_keys(self):
        found = load_sections(SOURCE_ROOT)
        for key in ("mandate", "off-limits", "workaround-log", "general", "company_site", "sitemaps", "careers",
                    "video", "podcasts", "transcription", "social", "independent_web", "archives", "pdf", "tooling"):
            self.assertIn(key, found, key)
        self.assertIs(found["company_site"], found["sitemaps"])
        self.assertIn("Greenhouse", found["careers"]["body"])

    def test_sections_ignore_headings_inside_fences(self):
        text = "## One (one)\n\n```bash\n## not a heading\n```\n\n## Two\n\nbody\n"
        found = sections(text)
        self.assertEqual(sorted(found), ["one", "two"])
        self.assertIn("## not a heading", found["one"]["body"])

    def test_section_keys_by_task(self):
        discovery = task("source_discovery", metadata={"channel": "careers"})
        self.assertEqual(section_keys(discovery), ["mandate", "off-limits", "workaround-log", "general", "careers"])
        capture = task("capture", inputs=[{"id": "S1", "url": "https://x.example/deck.pdf", "channel": "video", "source_kind": "page"}])
        self.assertEqual(section_keys(capture)[-3:], ["video", "transcription", "pdf"])
        self.assertEqual(section_keys(task("extraction")), ["mandate", "off-limits", "workaround-log", "pdf", "tooling"])
        self.assertEqual(section_keys(task("technical_review")), [])
        self.assertIn("company_site", section_keys(task("brand_guide")))

    def test_packet_carries_only_relevant_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("WORKFLOW.yaml", "RESEARCH_PLAYBOOK.md"):
                shutil.copy2(SOURCE_ROOT / name, root / name)
            shutil.copytree(SOURCE_ROOT / "prompts", root / "prompts")
            result = write_packet(root, task("source_discovery", metadata={"channel": "careers"}))
            body = (root / result["packet"]).read_text(encoding="utf-8")
            self.assertIn("## Research playbook", body)
            self.assertIn("Greenhouse", body)
            self.assertNotIn("yt-dlp", body)
            self.assertLess(body.index("## Research playbook"), body.index("## Lifecycle protocol"))
            packet = json.loads((root / result["packet_json"]).read_text(encoding="utf-8"))
            self.assertEqual(packet["playbook_sections"][-1], "careers")
            review = write_packet(root, task("technical_review"))
            self.assertNotIn("## Research playbook", (root / review["packet"]).read_text(encoding="utf-8"))

    def test_missing_playbook_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(playbook_for_task(Path(directory), task("capture")), ([], ""))

    def test_blocked_records_need_distinct_approaches(self):
        self.assertEqual(distinct_tried(["a -> 403", " a ->  403 ", "", "B -> timeout"]), ["a -> 403", "B -> timeout"])
        with self.assertRaises(ValueError):
            require_tried(["only one"], "x")
        self.assertEqual(len(require_tried(["one -> no", "two -> no"], "x")), MIN_TRIED)


if __name__ == "__main__":
    unittest.main()
