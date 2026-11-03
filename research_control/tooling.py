"""Install the tools a run needs, at the start of the run.

`setup` puts in place everything the runtime calls: yt-dlp, ffmpeg, and
faster-whisper for recordings (with the Whisper model and the speaker-labeling
models downloaded ahead of time), sherpa-onnx for speaker labels, poppler for
PDFs, and Node with Playwright and its Chromium for the headless browser and
PDF printing. Every step is recorded as present, installed, failed (with the
reason), or skipped, and nothing here blocks a run: what could not be
installed shows up as a preflight warning and a capture method falls back.
`start`, `new`, and `resume` run it before anything else; `setup` runs it by
hand to retry.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from research_control.io import atomic_write_json, utc_now

REPORT = "runs/_setup/setup-report.json"
RUN_REPORT = "tools/outputs/setup-report.json"
PYTHON_PACKAGES = {
    "yt-dlp": ("yt_dlp", "captions and audio from video and podcast pages"),
    "faster-whisper": ("faster_whisper", "local transcription"),
    "numpy": ("numpy", "audio decoding for transcription"),
    "sherpa-onnx": ("sherpa_onnx", "speaker labels in transcripts"),
}
APT_PACKAGES = {"ffmpeg": "ffmpeg", "pdftotext": "poppler-utils", "pdftoppm": "poppler-utils", "node": "nodejs", "npm": "npm", "git": "git"}
BREW_PACKAGES = {"ffmpeg": "ffmpeg", "pdftotext": "poppler", "pdftoppm": "poppler", "node": "node", "npm": "node", "git": "git"}
STEP_TIMEOUT = 900
Runner = Callable[..., subprocess.CompletedProcess]


class Setup:
    def __init__(self, template_root: Path, *, models: bool = True, runner: Runner | None = None,
                 which: Callable[[str], str | None] | None = None) -> None:
        self.root = template_root.resolve()
        self.models = models
        self.runner = runner or subprocess.run
        self.which = which or shutil.which
        self.steps: list[dict[str, str]] = []

    # -- recording -----------------------------------------------------------------
    def record(self, tool: str, status: str, detail: str = "") -> None:
        self.steps.append({"tool": tool, "status": status, "detail": detail[:400]})

    def run(self, command: list[str], *, timeout: int = STEP_TIMEOUT, cwd: Path | None = None,
            env: dict[str, str] | None = None) -> tuple[int, str]:
        try:
            result = self.runner(
                command, text=True, capture_output=True, timeout=timeout, cwd=str(cwd) if cwd else None,
                env={**os.environ, **(env or {})},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return 1, f"{type(error).__name__}: {error}"
        output = (result.stderr or "") + (result.stdout or "")
        return result.returncode, output.strip()[-600:]

    # -- system packages -----------------------------------------------------------
    def _sudo(self) -> list[str]:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return []
        if self.which("sudo") and self.run(["sudo", "-n", "true"], timeout=30)[0] == 0:
            return ["sudo", "-n"]
        return ["__no_root__"]

    def system_install(self, tools: list[str]) -> None:
        """apt-get on Debian and Ubuntu, Homebrew on macOS; by hand elsewhere."""
        missing = [tool for tool in tools if not self.which(tool)]
        if not missing:
            return
        if self.which("apt-get"):
            prefix = self._sudo()
            if prefix == ["__no_root__"]:
                for tool in missing:
                    self.record(tool, "failed", f"needs root to apt-get install {APT_PACKAGES[tool]}; install it by hand")
                return
            packages = sorted({APT_PACKAGES[tool] for tool in missing})
            env = {"DEBIAN_FRONTEND": "noninteractive"}
            code, output = self.run([*prefix, "apt-get", "install", "-y", "-q", *packages], env=env)
            if code != 0 and "Unable to locate" in output:
                self.run([*prefix, "apt-get", "update", "-q"], env=env)
                code, output = self.run([*prefix, "apt-get", "install", "-y", "-q", *packages], env=env)
            for tool in missing:
                if self.which(tool):
                    self.record(tool, "installed", f"apt-get install {APT_PACKAGES[tool]}")
                else:
                    self.record(tool, "failed", f"apt-get install {APT_PACKAGES[tool]}: {output}")
            return
        if self.which("brew"):
            for tool in missing:
                code, output = self.run(["brew", "install", "--quiet", BREW_PACKAGES[tool]])
                self.record(tool, "installed" if self.which(tool) else "failed", f"brew install {BREW_PACKAGES[tool]}" + ("" if code == 0 else f": {output}"))
            return
        for tool in missing:
            self.record(tool, "failed", f"no package manager found; install {tool} by hand")

    # -- python packages -----------------------------------------------------------
    def _importable(self, module: str) -> bool:
        code, _output = self.run([sys.executable, "-c", f"import {module}"], timeout=120)
        return code == 0

    def pip_install(self, package: str, module: str, purpose: str) -> None:
        if self._importable(module) and (package != "yt-dlp" or self.which("yt-dlp")):
            self.record(package, "present", purpose)
            return
        base = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--upgrade", package]
        attempts = [base, [*base, "--user"], [*base, "--break-system-packages"]]
        output = ""
        for command in attempts:
            code, output = self.run(command)
            if code == 0 and self._importable(module):
                extra = " ".join(flag for flag in command if flag in {"--user", "--break-system-packages"})
                self.record(package, "installed", f"pip install {package}{' ' + extra if extra else ''}; {purpose}")
                if package == "yt-dlp" and not self.which("yt-dlp"):
                    self._link_user_script("yt-dlp")
                return
        self.record(package, "failed", f"pip install {package}: {output}")

    def _link_user_script(self, name: str) -> None:
        """A --user install puts scripts in ~/.local/bin, which may be off PATH."""
        candidate = Path.home() / ".local/bin" / name
        if candidate.is_file():
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                target = Path(directory) / name
                try:
                    if directory and os.access(directory, os.W_OK) and not target.exists():
                        target.symlink_to(candidate)
                        self.record(f"{name} on PATH", "installed", f"{target} -> {candidate}")
                        return
                except OSError:
                    continue
            self.record(f"{name} on PATH", "failed", f"{candidate} exists but no PATH directory is writable; add ~/.local/bin to PATH")

    # -- node, playwright, chromium ------------------------------------------------
    def playwright(self) -> None:
        if not self.which("node"):
            self.record("playwright", "failed", "node is not installed, so there is no headless browser")
            return
        probe = ["node", "-e", "require('playwright')"]
        if self.run(probe, timeout=60, cwd=self.root)[0] != 0:
            if not self.which("npm"):
                self.record("playwright", "failed", "npm is not installed; install Node with npm, then rerun setup")
                return
            code, output = self.run(
                ["npm", "install", "--no-save", "--no-package-lock", "--no-audit", "--no-fund", "playwright"], cwd=self.root,
            )
            if code != 0 or self.run(probe, timeout=60, cwd=self.root)[0] != 0:
                self.record("playwright", "failed", f"npm install playwright: {output}")
                return
            self.record("playwright", "installed", f"npm install playwright in {self.root} (node_modules is ignored by git)")
        else:
            self.record("playwright", "present", "require('playwright') resolves")
        code, path = self.run(
            ["node", "-e", "process.stdout.write(require('playwright').chromium.executablePath())"], timeout=60, cwd=self.root,
        )
        if code == 0 and path and Path(path).is_file():
            self.record("chromium", "present", path)
            return
        with_deps = ["--with-deps"] if self._sudo() != ["__no_root__"] and self.which("apt-get") else []
        code, output = self.run(["npx", "--yes", "playwright", "install", *with_deps, "chromium"], cwd=self.root)
        code2, path = self.run(
            ["node", "-e", "process.stdout.write(require('playwright').chromium.executablePath())"], timeout=60, cwd=self.root,
        )
        if code == 0 and code2 == 0 and path and Path(path).is_file():
            self.record("chromium", "installed", f"playwright install chromium: {path}")
        else:
            self.record("chromium", "failed", f"playwright install chromium: {output}")

    # -- models --------------------------------------------------------------------
    def download_models(self) -> None:
        from research_control.media import WHISPER_MODEL

        script = (
            "from faster_whisper import WhisperModel; "
            f"WhisperModel({WHISPER_MODEL!r}, device='cpu', compute_type='int8'); print('ready')"
        )
        code, output = self.run([sys.executable, "-c", script], timeout=1800)
        self.record(f"whisper model {WHISPER_MODEL}", "present" if code == 0 else "failed", "" if code == 0 else output)
        script = "from research_control.media import _diarization_models; print(_diarization_models())"
        code, output = self.run([sys.executable, "-c", script], timeout=1800, cwd=self.root)
        self.record("speaker-label models", "present" if code == 0 else "failed", "" if code == 0 else output)

    # -- the whole thing -----------------------------------------------------------
    def install(self) -> dict[str, Any]:
        self.system_install(["git", "ffmpeg", "pdftotext", "pdftoppm", "node", "npm"])
        for tool in ("git", "ffmpeg", "pdftotext", "pdftoppm", "node", "npm"):
            if self.which(tool) and not any(step["tool"] == tool for step in self.steps):
                self.record(tool, "present", self.which(tool) or "")
        for package, (module, purpose) in PYTHON_PACKAGES.items():
            self.pip_install(package, module, purpose)
        self.playwright()
        if self.models:
            if any(step["tool"] == "faster-whisper" and step["status"] != "failed" for step in self.steps):
                self.download_models()
            else:
                self.record("models", "skipped", "faster-whisper is not installed")
        else:
            self.record("models", "skipped", "--no-models")
        failed = [step for step in self.steps if step["status"] == "failed"]
        report = {
            "status": "ready" if not failed else "partial",
            "at": utc_now(),
            "platform": f"{platform.system()} {platform.release()}",
            "python": sys.version.split()[0],
            "steps": self.steps,
            "missing": [f"{step['tool']}: {step['detail']}" for step in failed],
        }
        atomic_write_json(self.root / REPORT, report)
        return report


def install_tools(template_root: Path, *, models: bool = True, runner: Runner | None = None,
                  which: Callable[[str], str | None] | None = None) -> dict[str, Any]:
    return Setup(template_root, models=models, runner=runner, which=which).install()


def record_setup(template_root: Path, run_root: Path) -> None:
    """Keep the tool report with the run, so its archive says what the machine had."""
    from research_control.orchestration import append_history

    source = template_root / REPORT
    if not source.is_file():
        return
    shutil.copyfile(source, run_root / RUN_REPORT)
    report = json.loads(source.read_text(encoding="utf-8"))
    counts = {status: sum(1 for step in report["steps"] if step["status"] == status) for status in ("present", "installed", "failed", "skipped")}
    summary = ", ".join(f"{count} {status}" for status, count in counts.items() if count)
    missing = "; ".join(report["missing"]) if report["missing"] else "nothing missing"
    append_history(run_root, "tools", f"{summary}; {missing}")


def summary(report: dict[str, Any]) -> dict[str, Any]:
    """The short form `start` and `new` print."""
    return {
        "status": report["status"],
        "installed": [step["tool"] for step in report["steps"] if step["status"] == "installed"],
        "missing": report["missing"],
        "report": REPORT,
    }
