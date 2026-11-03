import tempfile
import unittest
from pathlib import Path

from research_control import FAIL, PASS, UNKNOWN
from research_control.io import load_json, load_jsonl
from research_control.worker_ledger import LEDGER, LedgerError, finish, launch, read_input_list, summary
from research_control.tests.helpers import validation, write_json


class WorkerLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "prompts/core").mkdir(parents=True)
        (self.root / "prompts/phases").mkdir(parents=True)
        (self.root / "prompts/core/runtime.md").write_text("runtime\n", encoding="utf-8")
        (self.root / "prompts/phases/capture.md").write_text("capture\n", encoding="utf-8")
        (self.root / "tools/lists").mkdir(parents=True)
        (self.root / "tools/lists/pages.csv").write_text("source_id,url\nS1,a\nS2,b\nS3,c\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _launch(self, task="cap-1", **extra):
        return launch(self.root, task_id=task, task_type="capture", input_ids=["S1", "S2"],
                      outputs=["out/part.csv"], validators=["capture_records"], **extra)

    def test_launch_registers_row_assignment_and_scratch(self):
        row, assignment, message = self._launch()
        self.assertEqual((row["status"], row["attempt"], row["worker_id"]), ("running", 1, "cap-1-a1"))
        self.assertEqual(load_jsonl(self.root / LEDGER), [row])
        record = load_json(assignment)
        self.assertTrue(record["immutable"])
        self.assertEqual(record["read_first"], ["prompts/core/runtime.md", "prompts/phases/capture.md"])
        self.assertTrue((self.root / "scratchpad/cap-1-a1").is_dir())
        self.assertIn("TASK TYPE: CAPTURE WORK, NOT A STATUS QUESTION", message)
        self.assertIn("tools/outputs/assignments/cap-1-1.json", message)

    def test_second_launch_needs_terminal_first_attempt_then_increments(self):
        self._launch()
        with self.assertRaises(LedgerError):
            self._launch()
        (self.root / "out").mkdir()
        (self.root / "out/part.csv").write_text("x\n", encoding="utf-8")
        finish(self.root, task_id="cap-1", status="failed", validation=FAIL)
        row, _, _ = self._launch()
        self.assertEqual(row["attempt"], 2)
        self.assertEqual(len(load_jsonl(self.root / LEDGER)), 2)

    def test_finish_success_hashes_outputs_and_ledger_passes(self):
        self._launch()
        (self.root / "out").mkdir()
        (self.root / "out/part.csv").write_text("S1\nS2\n", encoding="utf-8")
        write_json(self.root / "tools/outputs/validations/cap-1.json", validation())
        row, problems, report = finish(self.root, task_id="cap-1", status="succeeded",
                                       validator_reports=["tools/outputs/validations/cap-1.json"], exit_status=0)
        self.assertEqual((row["status"], row["output_validation_status"], problems), ("succeeded", PASS, []))
        self.assertIn("out/part.csv", row["output_hashes"])
        self.assertEqual(report["status"], PASS)
        self.assertEqual(len(load_jsonl(self.root / LEDGER)), 1)

    def test_finish_downgrades_success_without_output_or_validation(self):
        self._launch()
        row, problems, report = finish(self.root, task_id="cap-1", status="succeeded", validation=PASS)
        self.assertEqual(row["status"], "failed")
        self.assertTrue(any("output missing" in item for item in problems))
        self.assertEqual(report["status"], FAIL)
        (self.root / "out").mkdir()
        (self.root / "out/part.csv").write_text("x\n", encoding="utf-8")
        row, _, _ = self._launch()
        row, problems, _ = finish(self.root, task_id="cap-1", status="succeeded")
        self.assertEqual((row["status"], row["output_validation_status"]), ("failed", UNKNOWN))

    def test_finish_twice_is_refused(self):
        self._launch()
        finish(self.root, task_id="cap-1", status="blocked", validation=UNKNOWN)
        with self.assertRaises(LedgerError):
            finish(self.root, task_id="cap-1", status="failed")

    def test_input_list_slicing(self):
        path = self.root / "tools/lists/pages.csv"
        self.assertEqual(read_input_list(path, None), ["S1", "S2", "S3"])
        self.assertEqual(read_input_list(path, "2-3"), ["S2", "S3"])
        with self.assertRaises(LedgerError):
            read_input_list(path, "2-9")

    def test_summary_counts_latest_attempts(self):
        self._launch()
        finish(self.root, task_id="cap-1", status="blocked", validation=UNKNOWN)
        self._launch()
        text = summary(self.root)
        self.assertIn("2 attempts across 1 tasks", text)
        self.assertIn("capture: 1 running", text)
        self.assertIn("open: cap-1", text)


if __name__ == "__main__":
    unittest.main()
