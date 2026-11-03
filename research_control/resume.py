"""Resume a run from its archive on the remote, on any machine.

`archive` keeps a run on its own branch of the template's remote. `resume`
is the other half: from a fresh template checkout it fetches that branch into
`runs/<slug>`, restores the scheduler database from the archived snapshot,
syncs the engine this checkout has, and releases the leases that workers on
the old machine still held. `run` then continues where the archive left off,
and later archives extend the same branch.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from research_control.archive import ARCHIVE_GIT, EXCLUDES, SNAPSHOT_DB, _git
from research_control.io import atomic_write_text
from research_control.orchestration import append_history
from research_control.provision import RUNS_DIRECTORY, run_slug, sync_engine
from research_control.runtime import RuntimeStore

LIVE_DB = "tools/outputs/runtime.sqlite3"
RUN_STATE = "tools/outputs/run-state.json"
LEASED_STATES = {"leased", "running", "validating"}


def template_remote(template_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(template_root), "remote", "get-url", "origin"], text=True, capture_output=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("the template checkout has no origin remote; pass --remote")
    return result.stdout.strip()


def resume_run(
    template_root: Path,
    *,
    slug: str | None = None,
    url: str | None = None,
    branch: str | None = None,
    remote: str | None = None,
    run_root: Path | None = None,
) -> dict[str, Any]:
    template_root = template_root.resolve()
    if not (slug or url or branch):
        raise ValueError("pass --url, --slug, or --branch to say which run to resume")
    slug = slug or (branch.rsplit("/", 1)[-1] if branch else run_slug(url or ""))
    branch = branch or f"run-data/{slug}"
    run_root = (run_root or template_root / RUNS_DIRECTORY / slug).resolve()
    if (run_root / RUN_STATE).is_file():
        raise FileExistsError(f"a run already exists at {run_root}; continue it with `python3 -m research_control run`")
    remote = remote or template_remote(template_root)

    run_root.mkdir(parents=True, exist_ok=True)
    git_dir = run_root / ARCHIVE_GIT
    if not git_dir.is_dir():
        subprocess.run(["git", "init", "--quiet", "--bare", str(git_dir)], check=True)
        _git(run_root, "config", "core.bare", "false")
        _git(run_root, "config", "user.name", os.environ.get("GIT_AUTHOR_NAME", "research-control"))
        _git(run_root, "config", "user.email", os.environ.get("GIT_AUTHOR_EMAIL", "research-control@localhost"))
    atomic_write_text(git_dir / "info/exclude", "\n".join(EXCLUDES) + "\n")
    head_ref = _git(run_root, "symbolic-ref", "HEAD").stdout.strip() or "refs/heads/master"
    # Git refuses to fetch straight into the checked-out branch, so the archive lands in a
    # temporary ref and the branch is pointed at it.
    fetched = _git(run_root, "fetch", "--quiet", remote, f"refs/heads/{branch}:refs/resume/incoming", check=False)
    if fetched.returncode != 0:
        raise RuntimeError(f"could not fetch {branch} from {remote}: {(fetched.stderr or fetched.stdout).strip()[:300]}")
    _git(run_root, "update-ref", head_ref, "refs/resume/incoming")
    _git(run_root, "update-ref", "-d", "refs/resume/incoming")
    _git(run_root, "read-tree", "HEAD")
    _git(run_root, "checkout-index", "-a", "-f")
    commit = _git(run_root, "rev-parse", "HEAD").stdout.strip()
    if not (run_root / RUN_STATE).is_file():
        raise RuntimeError(f"{branch} holds no run state; it is not an archived run")

    restored_db = False
    snapshot = run_root / SNAPSHOT_DB
    live = run_root / LIVE_DB
    if snapshot.is_file() and not live.is_file():
        with sqlite3.connect(snapshot) as source, sqlite3.connect(live) as copy:
            source.backup(copy)
        restored_db = True

    synced = sync_engine(template_root, run_root)

    released: list[str] = []
    if live.is_file():
        with RuntimeStore(run_root) as store:
            for task in store.tasks(states=LEASED_STATES):
                store.fail(
                    task["task_id"], task["lease_owner"] or "unknown",
                    "run resumed from its archive; the lease was held on another machine", retryable=True,
                )
                released.append(task["task_id"])
    append_history(
        run_root, "resumed",
        f"from {branch} at {commit[:12]} ({remote}); scheduler {'restored from snapshot' if restored_db else 'already present'}; "
        f"leases released: {len(released)}",
    )
    return {
        "status": "resumed",
        "run_root": str(run_root),
        "branch": branch,
        "commit": commit,
        "remote": remote,
        "scheduler_restored": restored_db,
        "leases_released": released,
        "engine_synced": synced,
        "next": "python3 -m research_control run",
    }
