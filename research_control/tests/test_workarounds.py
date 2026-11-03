from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from research_control.io import load_jsonl
from research_control.workarounds import LOG, REPORT, add_workaround, render_workarounds

SOURCE_ROOT = Path(__file__).resolve().parents[2]


class WorkaroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copy2(SOURCE_ROOT / "RESEARCH_PLAYBOOK.md", self.root / "RESEARCH_PLAYBOOK.md")

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_report(self):
        path = render_workarounds(self.root)
        self.assertEqual(path, self.root / REPORT)
        self.assertIn("No workarounds recorded yet.", path.read_text(encoding="utf-8"))

    def test_add_appends_log_and_renders_grouped_report(self):
        add_workaround(self.root, task_id="capture.discover.careers", channel="careers", target="boards.greenhouse.io",
                       failure="403 from hosted board", tried=["rendered board page -> 403"],
                       worked="boards-api JSON with token from embed script", items=12, applies="platform",
                       playbook_change="add token-from-embed-script step", worker_id="w1")
        add_workaround(self.root, task_id="capture.source.s9", channel="video", target="youtube.com",
                       failure="no subtitles", tried=["web_embedded -> none"], worked="player_client=mweb")
        rows = load_jsonl(self.root / LOG)
        self.assertEqual([row["channel"] for row in rows], ["careers", "video"])
        text = (self.root / REPORT).read_text(encoding="utf-8")
        self.assertIn("2 entries.", text)
        self.assertLess(text.index("## Careers"), text.index("## Video"))
        self.assertIn("**Items:** 12", text)
        self.assertIn("player_client=mweb", text)
        self.assertIn("(worker `w1`)", text)

    def test_add_rejects_unknown_channel_and_empty_tried(self):
        with self.assertRaises(ValueError):
            add_workaround(self.root, task_id="t", channel="nope", target="x", failure="y", tried=["a"], worked="z")
        with self.assertRaises(ValueError):
            add_workaround(self.root, task_id="t", channel="careers", target="x", failure="y", tried=[" "], worked="z")
        self.assertFalse((self.root / LOG).exists())


if __name__ == "__main__":
    unittest.main()
