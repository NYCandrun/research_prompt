import tempfile
import unittest
from pathlib import Path

from research_control.workarounds import OUTPUT, merge, playbook_channels

PLAYBOOK = """# Research playbook

## Mandate
## Off-limits
## When a workaround works
## Every channel
## YouTube
## Careers
"""

PART_A = """# Worker capture-video-1

### 2026-11-02 · YouTube · Captions empty with web_embedded

- **Failure:** no subtitles returned
- **Worked:** `--extractor-args "youtube:player_client=mweb"`
"""

PART_B = """### 2026-11-01 · careers · Greenhouse token was hidden

- **Worked:** token from embed script URL

### no date here
- **Worked:** something
"""


class WorkaroundMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "RESEARCH_PLAYBOOK.md").write_text(PLAYBOOK, encoding="utf-8")
        (self.root / "workarounds").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_channels_come_from_playbook(self):
        self.assertEqual(playbook_channels(self.root), ["YouTube", "Careers"])

    def test_empty_log_is_still_written(self):
        path, count, problems = merge(self.root)
        self.assertEqual((count, problems), (0, []))
        self.assertIn("No workarounds recorded yet.", path.read_text(encoding="utf-8"))

    def test_entries_grouped_by_channel_and_malformed_kept(self):
        (self.root / "workarounds/2026-11-02-video-1.md").write_text(PART_A, encoding="utf-8")
        (self.root / "workarounds/2026-11-01-careers-1.md").write_text(PART_B, encoding="utf-8")
        _, count, problems = merge(self.root)
        text = (self.root / OUTPUT).read_text(encoding="utf-8")
        self.assertEqual(count, 3)
        self.assertEqual(len(problems), 1)
        self.assertLess(text.index("## YouTube"), text.index("## Careers"))
        self.assertLess(text.index("## Careers"), text.index("## Other"))
        self.assertIn("player_client=mweb", text)
        self.assertIn("### no date here", text.replace("0000-00-00 · ", ""))

    def test_merge_is_deterministic(self):
        (self.root / "workarounds/a.md").write_text(PART_A, encoding="utf-8")
        merge(self.root)
        first = (self.root / OUTPUT).read_text(encoding="utf-8")
        merge(self.root)
        self.assertEqual(first, (self.root / OUTPUT).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
