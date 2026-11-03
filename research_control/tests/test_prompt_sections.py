import tempfile
import unittest
from pathlib import Path

from research_control.prompt_sections import listing, section, section_text, sections

PROMPT = """# Company research prompt

Intro line.

## -1. Runtime

runtime text

### Repository rules

rule text

## 0. Language

language text

## 15. Phase 6

phase six

## 15.3 Citation system

```bash
# not a heading inside a fence
## 99. also not a heading
```

citations

# 17. Done means

done

# Amendment: execution integrity

preamble

## 19. Execution integrity

ledger
"""


class PromptSectionTests(unittest.TestCase):
    def test_sections_merge_subsections_and_attach_preamble(self):
        keys = [item.key for item in sections(PROMPT)]
        self.assertEqual(keys, ["intro", "-1", "0", "15", "17", "19"])
        lines = PROMPT.splitlines()
        self.assertIn("rule text", section(PROMPT, "-1").text(lines))
        fifteen = section(PROMPT, "15").text(lines)
        self.assertIn("## 15.3 Citation system", fifteen)
        self.assertIn("## 99. also not a heading", fifteen)
        self.assertNotIn("done", fifteen)
        nineteen = section(PROMPT, "19").text(lines)
        self.assertTrue(nineteen.startswith("# Amendment"))
        self.assertIn("ledger", nineteen)
        self.assertNotIn("preamble", section(PROMPT, "17").text(lines))

    def test_section_text_and_listing_from_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "README.md"
            path.write_text(PROMPT, encoding="utf-8")
            text = section_text(path, ["0", "17"])
            self.assertIn("language text", text)
            self.assertIn("done", text)
            self.assertIn("-1 ", listing(path))
            with self.assertRaises(KeyError):
                section_text(path, ["42"])

    def test_real_readme_covers_every_line_once(self):
        root = Path(__file__).resolve().parents[2]
        text = (root / "README.md").read_text(encoding="utf-8")
        found = sections(text)
        self.assertEqual(found[0].start, 0)
        self.assertEqual(found[-1].end, len(text.splitlines()))
        for earlier, later in zip(found, found[1:]):
            self.assertEqual(earlier.end, later.start)
        self.assertEqual(len({item.key for item in found}), len(found))
        for key in ["-1", "0", "7", "8", "10", "15", "16", "17", "18", "19"]:
            section(text, key)


if __name__ == "__main__":
    unittest.main()
