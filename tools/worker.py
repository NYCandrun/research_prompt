#!/usr/bin/env python3
"""Worker bookkeeping in one call each: launch, finish, status.

  launch  registers a running attempt in the ledger, writes an immutable
          assignment file, creates the scratch directory, and prints the
          two-line worker prompt to send.
  finish  hashes the expected outputs, records the terminal status and
          validation result on that attempt's row, and validates the ledger.
  status  prints attempt counts by task type from the ledger.

Examples:
  python3 tools/worker.py launch --task-id cap-web-01 --task-type capture \\
      --input-list tools/lists/web-pages.csv --rows 1-50 \\
      --output 01-sources/manifest-parts/cap-web-01.csv \\
      --output 01-sources/blocked-parts/cap-web-01.md --validator capture_records
  python3 tools/worker.py finish --task-id cap-web-01 --status succeeded \\
      --validator-report tools/outputs/validations/cap-web-01.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_control import PASS
from research_control.worker_ledger import LEDGER, LedgerError, finish, launch, read_input_list, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ledger", default=LEDGER)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("launch")
    run.add_argument("--task-id", required=True)
    run.add_argument("--task-type", required=True)
    run.add_argument("--worker-id")
    run.add_argument("--workflow-id")
    run.add_argument("--input-id", action="append", default=[], help="repeatable")
    run.add_argument("--input-list", type=Path, help="CSV (first column, header skipped) or one ID per line")
    run.add_argument("--rows", help="1-based inclusive slice of the input list, such as 1-50")
    run.add_argument("--non-exclusive", action="store_true", help="inputs may also be assigned to other tasks")
    run.add_argument("--output", action="append", default=[], required=True, help="repeatable, repo-relative")
    run.add_argument("--validator", action="append", default=[], help="repeatable")
    run.add_argument("--scratch", help="defaults to scratchpad/<worker-id>/")
    run.add_argument("--prompt", action="append", help="prompt files to read; defaults to runtime core plus the phase prompt")
    run.add_argument("--brief", help="run-specific phase brief to read")
    run.add_argument("--note")

    done = sub.add_parser("finish")
    done.add_argument("--task-id", required=True)
    done.add_argument("--attempt", type=int, help="defaults to the latest attempt")
    done.add_argument("--status", required=True, choices=["succeeded", "failed", "blocked"])
    done.add_argument("--exit-status")
    done.add_argument("--validation", choices=["PASS", "FAIL", "UNKNOWN"])
    done.add_argument("--validator-report", action="append", default=[], help="repeatable; overrides --validation")
    done.add_argument("--note")

    sub.add_parser("status")
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.command == "launch":
            ids = list(args.input_id)
            if args.input_list:
                ids += read_input_list(root / args.input_list if not args.input_list.is_absolute() else args.input_list, args.rows)
            elif args.rows:
                raise LedgerError("--rows needs --input-list")
            row, assignment, message = launch(
                root, task_id=args.task_id, task_type=args.task_type, input_ids=ids, outputs=args.output,
                validators=args.validator, worker_id=args.worker_id, workflow_id=args.workflow_id,
                exclusive=not args.non_exclusive, scratch=args.scratch, prompts=args.prompt, brief=args.brief,
                note=args.note, ledger=args.ledger,
            )
            print(f"registered {row['task_id']} attempt {row['attempt']} ({len(ids)} inputs) -> {assignment.relative_to(root)}")
            print("--- worker prompt ---")
            sys.stdout.write(message)
        elif args.command == "finish":
            exit_status: int | str | None = args.exit_status
            if isinstance(exit_status, str) and exit_status.lstrip("-").isdigit():
                exit_status = int(exit_status)
            row, problems, report = finish(
                root, task_id=args.task_id, attempt=args.attempt, status=args.status, exit_status=exit_status,
                validation=args.validation, validator_reports=args.validator_report, note=args.note, ledger=args.ledger,
            )
            print(f"{row['task_id']} attempt {row['attempt']}: {row['status']} validation={row['output_validation_status']} hashed={len(row['output_hashes'])}")
            for problem in problems:
                print(f"  problem: {problem}")
            print(f"ledger[{row['task_type']}]: {report['status']}" + (f" ({len(report['failures'])} failures, {len(report['unknowns'])} unknown)" if report["status"] != PASS else ""))
            for item in (report["failures"] + report["unknowns"])[:5]:
                print(f"  {item}")
            raise SystemExit(0 if row["status"] == "succeeded" or args.status != "succeeded" else 1)
        else:
            sys.stdout.write(summary(root, args.ledger))
    except LedgerError as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
