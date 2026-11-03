from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from research_control.io import load_json
from research_control.orchestration import initialize
from research_control.provision import provision_run
from research_control.tooling import REPORT, RUN_REPORT, install_tools, record_setup, summary

SOURCE_ROOT = Path(__file__).resolve().parents[2]


class FakeMachine:
    """A machine where some tools exist; commands either succeed or fail by rule."""

    def __init__(self, present: set[str], importable: set[str], fail: set[str] = frozenset()) -> None:
        self.present = set(present)
        self.importable = set(importable)
        self.fail = set(fail)
        self.commands: list[list[str]] = []

    def which(self, name: str) -> str | None:
        return f"/usr/bin/{name}" if name in self.present else None

    def run(self, command, **_kwargs) -> subprocess.CompletedProcess:
        self.commands.append(list(command))
        joined = " ".join(command)
        if "-c" in command and command[-1].startswith("import "):
            module = command[-1].split()[1]
            return subprocess.CompletedProcess(command, 0 if module in self.importable else 1, "", "No module")
        if "pip" in joined and "install" in joined:
            package = command[command.index("--upgrade") + 1]
            if package in self.fail:
                return subprocess.CompletedProcess(command, 1, "", "error: externally-managed-environment")
            self.importable.add(package.replace("-", "_"))
            if package == "yt-dlp":
                self.present.add("yt-dlp")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "apt-get" in joined and "install" in joined:
            for tool, package in (("ffmpeg", "ffmpeg"), ("pdftotext", "poppler-utils"), ("pdftoppm", "poppler-utils")):
                if package in command and package not in self.fail:
                    self.present.add(tool)
            return subprocess.CompletedProcess(command, 0, "", "")
        if "require('playwright')" in joined and "executablePath" not in joined:
            return subprocess.CompletedProcess(command, 0 if "playwright" in self.present else 1, "", "Cannot find module")
        if "npm" in command and "install" in command:
            self.present.add("playwright")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "executablePath" in joined:
            return subprocess.CompletedProcess(command, 0, "/nonexistent/chrome", "")
        if "playwright" in joined and "install" in joined:
            return subprocess.CompletedProcess(command, 1, "", "download failed")
        if "sudo" in command:
            return subprocess.CompletedProcess(command, 1, "", "")
        return subprocess.CompletedProcess(command, 0, "ready", "")


class ToolingTests(unittest.TestCase):
    def test_everything_present_installs_nothing(self) -> None:
        machine = FakeMachine(
            present={"git", "ffmpeg", "pdftotext", "pdftoppm", "node", "npm", "yt-dlp", "playwright"},
            importable={"yt_dlp", "faster_whisper", "numpy", "sherpa_onnx"},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = install_tools(root, models=False, runner=machine.run, which=machine.which)
            self.assertEqual([step["status"] for step in report["steps"] if step["tool"] != "chromium"].count("installed"), 0)
            self.assertEqual(
                {step["tool"]: step["status"] for step in report["steps"]}["playwright"], "present"
            )
            self.assertFalse(any("pip" in " ".join(command) and "install" in command for command in machine.commands))
            self.assertTrue((root / REPORT).is_file())

    def test_missing_tools_are_installed_and_failures_are_recorded_not_raised(self) -> None:
        machine = FakeMachine(present={"git", "node", "npm", "apt-get"}, importable={"numpy"}, fail={"sherpa-onnx"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = install_tools(root, models=False, runner=machine.run, which=machine.which)
            status = {step["tool"]: step["status"] for step in report["steps"]}
            self.assertEqual(status["ffmpeg"], "installed")
            self.assertEqual(status["pdftotext"], "installed")
            self.assertEqual(status["yt-dlp"], "installed")
            self.assertEqual(status["faster-whisper"], "installed")
            self.assertEqual(status["sherpa-onnx"], "failed")
            self.assertEqual(status["playwright"], "installed")
            self.assertEqual(status["chromium"], "failed")
            self.assertEqual(report["status"], "partial")
            self.assertTrue(any("sherpa-onnx" in item for item in report["missing"]))
            pip_attempts = [command for command in machine.commands if "pip" in " ".join(command) and "sherpa-onnx" in command]
            self.assertEqual(len(pip_attempts), 3)
            self.assertIn("--break-system-packages", pip_attempts[-1])
            short = summary(report)
            self.assertIn("ffmpeg", short["installed"])

            run_root = root / "runs/acme"
            provision_run(SOURCE_ROOT, run_root)
            initialize(run_root, "https://acme.example")
            record_setup(root, run_root)
            self.assertEqual(load_json(run_root / RUN_REPORT)["status"], "partial")
            history = (run_root / "RUN_HISTORY.md").read_text(encoding="utf-8")
            self.assertIn("`tools`", history)
            self.assertIn("sherpa-onnx", history)


if __name__ == "__main__":
    unittest.main()
