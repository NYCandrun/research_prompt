"""Single-writer worker bookkeeping: register, finish, and summarize attempts.

One ledger row per attempt. `launch` appends a running row and writes an
immutable assignment file. `finish` hashes the outputs and rewrites that
attempt's row in place with its terminal status. The ledger file is always
rewritten atomically as a whole, so it needs one writer at a time.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from research_control import FAIL, PASS, UNKNOWN
from research_control.hashing import hash_path
from research_control.io import atomic_write_json, load_json, load_jsonl, utc_now
from research_control.reconciliation.assignments import validate_ledger

LEDGER = "tools/outputs/worker-ledger.jsonl"
ASSIGNMENTS = "tools/outputs/assignments"
TERMINAL = {"succeeded", "failed", "blocked"}


class LedgerError(Exception):
    pass


def read_ledger(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path) if path.is_file() else []


def write_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def read_input_list(path: Path, rows: str | None) -> list[str]:
    """IDs from a work list: first CSV column (header skipped) or one ID per line. `rows` is 1-based inclusive."""
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            records = list(csv.reader(handle))
        ids = [record[0].strip() for record in records[1:] if record and record[0].strip()]
    else:
        ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if rows:
        try:
            start, end = (int(part) for part in rows.split("-", 1))
        except ValueError as error:
            raise LedgerError(f"rows must look like 1-50, got {rows!r}") from error
        if start < 1 or end < start or end > len(ids):
            raise LedgerError(f"rows {rows} fall outside the {len(ids)} records in {path}")
        ids = ids[start - 1:end]
    return ids


def task_type_line(task_type: str) -> str:
    return f"TASK TYPE: {task_type.replace('_', ' ').replace('-', ' ').upper()} WORK, NOT A STATUS QUESTION"


def default_prompts(root: Path, task_type: str) -> list[str]:
    candidates = ["prompts/core/runtime.md", f"prompts/phases/{task_type.replace('_', '-')}.md"]
    return [item for item in candidates if (root / item).is_file()]


def launch(
    root: Path,
    *,
    task_id: str,
    task_type: str,
    input_ids: list[str],
    outputs: list[str],
    validators: list[str],
    worker_id: str | None = None,
    workflow_id: str | None = None,
    exclusive: bool = True,
    scratch: str | None = None,
    prompts: list[str] | None = None,
    brief: str | None = None,
    note: str | None = None,
    ledger: str = LEDGER,
) -> tuple[dict[str, Any], Path, str]:
    if not task_id.strip() or not task_type.strip():
        raise LedgerError("task_id and task_type are required")
    if not outputs:
        raise LedgerError("at least one --output is required")
    if len(set(input_ids)) != len(input_ids):
        raise LedgerError("input IDs contain duplicates")
    if len(set(outputs)) != len(outputs):
        raise LedgerError("output paths contain duplicates")
    ledger_path = root / ledger
    rows = read_ledger(ledger_path)
    previous = [row for row in rows if row.get("task_id") == task_id]
    if previous and previous[-1].get("status") not in TERMINAL:
        raise LedgerError(f"{task_id}: attempt {previous[-1].get('attempt')} is still {previous[-1].get('status')}; finish it first")
    attempt = max((int(row.get("attempt", 0)) for row in previous), default=0) + 1
    worker_id = worker_id or f"{task_id}-a{attempt}"
    scratch = scratch or f"scratchpad/{worker_id}/"
    prompts = prompts if prompts is not None else default_prompts(root, task_type)
    for relative in prompts + ([brief] if brief else []):
        if not (root / relative).is_file():
            raise LedgerError(f"prompt file not found: {relative}")
    assignment_path = root / ASSIGNMENTS / f"{task_id}-{attempt}.json"
    if assignment_path.exists():
        raise LedgerError(f"assignment file already exists: {assignment_path.relative_to(root)}")

    now = utc_now()
    row = {
        "worker_id": worker_id, "task_id": task_id, "workflow_id": workflow_id, "attempt": attempt,
        "task_type": task_type, "input_ids": list(input_ids), "exclusive_inputs": exclusive,
        "expected_outputs": list(outputs), "required_validators": list(validators), "status": "running",
        "started_at": now, "finished_at": None, "exit_status": None, "output_validation_status": None,
        "output_hashes": {}, "assignment": assignment_path.relative_to(root).as_posix(),
    }
    assignment = {
        "immutable": True, "task_type_line": task_type_line(task_type),
        "worker_id": worker_id, "task_id": task_id, "attempt": attempt, "task_type": task_type,
        "workflow_id": workflow_id, "input_ids": list(input_ids), "input_count": len(input_ids),
        "exclusive_inputs": exclusive, "expected_outputs": list(outputs), "required_validators": list(validators),
        "scratch_directory": scratch, "read_first": prompts, "phase_brief": brief, "note": note,
        "ledger": ledger, "registered_at": now,
        "return_format": "At most about 10 lines: status, assigned count, completed count, exception count, output paths, validator result, blocked IDs.",
        "rules": [
            "Write only the expected outputs and the scratch directory.",
            "Do not edit the ledger, shared manifests, shared state, or another worker's files.",
            "You are done only when every expected output exists and its assigned validator passes.",
        ],
    }
    atomic_write_json(assignment_path, assignment)
    (root / scratch).mkdir(parents=True, exist_ok=True)
    rows.append(row)
    write_ledger(ledger_path, rows)
    reads = ", then ".join(f"`{item}`" for item in [assignment_path.relative_to(root).as_posix(), *prompts, *([brief] if brief else [])])
    message = f"{assignment['task_type_line']}\nRead {reads}. Do only that assignment and return in its return format.\n"
    return row, assignment_path, message


def _report_status(root: Path, report: str) -> str:
    path = root / report
    if not path.is_file() or path.stat().st_size == 0:
        return UNKNOWN
    try:
        value = load_json(path)
    except Exception:
        return UNKNOWN
    return value.get("status") if value.get("status") in {PASS, FAIL, UNKNOWN} else UNKNOWN


def finish(
    root: Path,
    *,
    task_id: str,
    status: str,
    attempt: int | None = None,
    exit_status: int | str | None = None,
    validation: str | None = None,
    validator_reports: list[str] | None = None,
    note: str | None = None,
    ledger: str = LEDGER,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    """Return (row, problems, ledger validation report). Problems downgrade `succeeded` to `failed`."""
    if status not in TERMINAL:
        raise LedgerError(f"status must be one of {sorted(TERMINAL)}")
    ledger_path = root / ledger
    rows = read_ledger(ledger_path)
    candidates = [row for row in rows if row.get("task_id") == task_id]
    if not candidates:
        raise LedgerError(f"{task_id}: no registered attempt")
    if attempt is None:
        attempt = max(int(row.get("attempt", 0)) for row in candidates)
    matches = [row for row in candidates if int(row.get("attempt", 0)) == attempt]
    if not matches:
        raise LedgerError(f"{task_id}: no attempt {attempt}")
    row = matches[0]
    if row.get("status") in TERMINAL:
        raise LedgerError(f"{task_id} attempt {attempt} already ended {row['status']}; retry with a new launch")

    problems: list[str] = []
    hashes: dict[str, str] = {}
    for output in row.get("expected_outputs", []):
        digest = hash_path(root / output)
        path = root / output
        if digest == "MISSING":
            problems.append(f"output missing: {output}")
        elif path.is_file() and path.stat().st_size == 0:
            problems.append(f"output empty: {output}")
            hashes[output] = digest
        else:
            hashes[output] = digest

    if validator_reports:
        statuses = {report: _report_status(root, report) for report in validator_reports}
        validation = PASS if all(value == PASS for value in statuses.values()) else FAIL if FAIL in statuses.values() else UNKNOWN
        for report, value in statuses.items():
            if value != PASS:
                problems.append(f"validator report {report}: {value}")
    elif validation not in {PASS, FAIL, UNKNOWN}:
        validation = UNKNOWN
        if status == "succeeded":
            problems.append("no validation result given for a succeeded attempt")
    elif validation != PASS and status == "succeeded":
        problems.append(f"validation is {validation}")

    if status == "succeeded" and problems:
        status = "failed"
    row.update({
        "status": status, "finished_at": utc_now(), "exit_status": exit_status,
        "output_validation_status": validation, "output_hashes": hashes,
    })
    if note or problems:
        row["notes"] = "; ".join(([note] if note else []) + problems)
    write_ledger(ledger_path, rows)
    report = validate_ledger(root, rows, {str(row.get("task_type"))})
    return row, problems, report


def summary(root: Path, ledger: str = LEDGER) -> str:
    rows = read_ledger(root / ledger)
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        task = str(row.get("task_id"))
        if task not in latest or int(row.get("attempt", 0)) > int(latest[task].get("attempt", 0)):
            latest[task] = row
    by_type: dict[str, dict[str, int]] = {}
    for row in latest.values():
        counts = by_type.setdefault(str(row.get("task_type")), {})
        counts[str(row.get("status"))] = counts.get(str(row.get("status")), 0) + 1
    lines = [f"{len(rows)} attempts across {len(latest)} tasks"]
    for task_type in sorted(by_type):
        parts = ", ".join(f"{count} {state}" for state, count in sorted(by_type[task_type].items()))
        lines.append(f"{task_type}: {parts}")
    open_tasks = sorted(task for task, row in latest.items() if row.get("status") not in TERMINAL)
    if open_tasks:
        lines.append("open: " + ", ".join(open_tasks[:20]) + (" ..." if len(open_tasks) > 20 else ""))
    return "\n".join(lines) + "\n"
