from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from research_control import adaptive
from research_control.adaptive import advance, complete_work
from research_control.archive import archive
from research_control.io import atomic_write_json, atomic_write_jsonl, atomic_write_text
from research_control.orchestration import initialize
from research_control.provision import provision_run
from research_control.resume import resume_run
from research_control.runtime import RuntimeStore, WorkItem

SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ResumeTests(unittest.TestCase):
    def test_a_run_resumes_from_its_archive_and_keeps_archiving_the_same_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "remote.git"
            subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True)
            transcript = base / "session.jsonl"
            transcript.write_text('{"type": "user", "message": "hello"}\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"RESEARCH_CONTROL_TRANSCRIPT": str(transcript)}):
                # The run on the first machine: state, a capture, a scheduler with a leased task.
                first = base / "machine-one/runs/acme"
                provision_run(SOURCE_ROOT, first)
                initialize(first, "https://acme.example")
                atomic_write_text(first / "01-sources/captures/SRC-1/content.txt", "Acme sells workflow software.\n")
                with RuntimeStore(first) as store:
                    store.initialize(run_id="acme-1", company_url="https://acme.example")
                    store.add_task(WorkItem(
                        task_id="capture.discover.careers", phase="capture", task_type="source_discovery",
                        inputs=[{"id": "channels", "value": ["careers"]}], outputs=["tools/outputs/worker-parts/discovery/careers.json"],
                        prompt_files=["prompts/core/runtime.md"], independent=True, exclusive_inputs=False,
                        metadata={"channels": ["careers"], "executor": "agent"},
                    ))
                    store.refresh_ready()
                    self.assertIsNotNone(store.claim("w-careers", task_id="capture.discover.careers"))
                    self.assertEqual(store.task("capture.discover.careers")["state"], "leased")
                saved = archive(first, remote=str(remote), push=True)
                self.assertTrue(saved["pushed"])

                # A second machine, with only the template and the remote.
                second = base / "machine-two/runs/acme"
                result = resume_run(SOURCE_ROOT, slug="acme", remote=str(remote), run_root=second)
                self.assertEqual(result["status"], "resumed")
                self.assertTrue(result["scheduler_restored"])
                self.assertEqual(result["leases_released"], ["capture.discover.careers"])
                self.assertEqual((second / "01-sources/captures/SRC-1/content.txt").read_text(encoding="utf-8"), "Acme sells workflow software.\n")
                self.assertTrue((second / "tools/outputs/run-state.json").is_file())
                self.assertTrue((second / "research_control/resume.py").is_file())
                with RuntimeStore(second) as store:
                    task = store.task("capture.discover.careers")
                    self.assertIn(task["state"], {"retryable", "ready"})
                    self.assertFalse(task["lease_owner"])
                self.assertIn("`resumed`", (second / "RUN_HISTORY.md").read_text(encoding="utf-8"))
                with self.assertRaises(FileExistsError):
                    resume_run(SOURCE_ROOT, slug="acme", remote=str(remote), run_root=second)

                # Work continues and the next archive extends the branch the first machine made.
                atomic_write_text(second / "01-sources/captures/SRC-2/content.txt", "A second page.\n")
                again = archive(second, remote=str(remote), push=True)
                self.assertTrue(again["committed"] and again["pushed"])
                count = subprocess.run(["git", "-C", str(remote), "rev-list", "--count", "run-data/acme"],
                                       text=True, capture_output=True, check=True).stdout.strip()
                self.assertEqual(count, "2")
                listed = subprocess.run(["git", "-C", str(remote), "ls-tree", "-r", "--name-only", "run-data/acme"],
                                        text=True, capture_output=True, check=True).stdout.split()
                self.assertIn("01-sources/captures/SRC-1/content.txt", listed)
                self.assertIn("01-sources/captures/SRC-2/content.txt", listed)

    def test_run_saves_and_confirms_before_a_phase_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            provision_run(SOURCE_ROOT, root)
            with mock.patch.dict(os.environ, {"RESEARCH_CONTROL_TRANSCRIPT": "/nonexistent/session.jsonl"}):
                advance(root, "https://acme.example", automatic=False)
                with RuntimeStore(root) as store:
                    self.assertIsNotNone(store.claim("w-scope", task_id="scope.scope"))
                    store.start("scope.scope", "w-scope")
                atomic_write_text(root / "00-scope.md", (
                    "# Scope\n\nCompany URL: https://acme.example\n\n## Inputs\nNo user inputs.\n\n## Source plan\n"
                    "First-party and third-party evidence.\n\n## Competitors\nComparable workflow products.\n\n"
                    "## Research questions\n\n**Q1. Product and architecture**\n\n**Q7. Competitors**\n"
                ))
                atomic_write_jsonl(root / "tools/outputs/input-classification.jsonl", [{
                    "assignment_id": "scope.scope", "input_id": "__none__", "disposition": "completed_zero",
                    "reason": "no user inputs", "evidence_paths": ["00-scope.md"], "output_ids": [],
                }])
                complete_work(root, "scope.scope", "w-scope")
                labels: list[str] = []

                def fake_push(run_root: Path, label: str) -> dict:
                    labels.append(label)
                    return {"on_remote": True, "status": "fake"}

                with mock.patch.object(adaptive, "ensure_conversation_pushed", side_effect=fake_push):
                    result = advance(root, automatic=False)
                self.assertIn("before the scope gate", labels)
                self.assertLess(labels.index("before the scope gate"), labels.index("start of capture"))
                self.assertEqual(result["phase"], "capture")


if __name__ == "__main__":
    unittest.main()
