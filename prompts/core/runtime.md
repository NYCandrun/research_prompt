# Runtime core

The orchestrator owns shared state. A worker edits only its exact output paths
and its private `scratchpad/<worker-label>/` directory. Do not edit the worker
ledger, `WORKFLOW_STATE.md`, `RUN_HISTORY.md`, shared manifests, global blocked
logs, citation maps, repository configuration, or another worker's output
unless the assignment names that shared-state responsibility.

The one infrastructure exception is the controlled `python3 -m research_control
web ...` interface. It may update the run-local URL ledger and immutable response
cache. That cache is transport only: a URL or cached object is not research
evidence, brand evidence, or a factual claim until the consuming packet admits
it through its own required evidence records.

## Assignment contract

Before work starts, the assignment must provide:

- task type and stable worker/task/attempt IDs;
- immutable input IDs or an exact work-list slice;
- exact output paths and scratch directory;
- required schema and validators;
- completion criteria and concise return format.

Do not infer placeholder arguments, unbounded input, ID ranges, or output paths.
Stop that assignment as blocked if one remains ambiguous, while unrelated work
continues.

## Completion

You are done only after the assigned output exists and its task-local check
passes. Return at most about 10 lines: status, assigned count, completed count,
exception count, output paths, validator result, and any blocked IDs. Detail
belongs in output files.

A progress message is not completion evidence. The orchestrator records hashes
and terminal status after inspecting outputs. Preserve partial resumable output
source by source. On interruption, inspect and resume. Do not duplicate
completed work.

Never write to a shared manifest or shared review file from parallel workers.
Write a worker-specific part for deterministic single-writer merge. Never
commit unrelated workers' files.

## Getting the data

Find the data as best you can. Your packet carries the playbook sections for
your task. Start with **Try first**, then **Then try**, then anything else you
can think of, until something works or five distinct approaches have failed.
Anything not on the off-limits list is allowed: no logins or accounts, no
paying or paywall-removal tricks, no live paths that `robots.txt` disallows.
Do not stop to judge an approach. A bot challenge is a failed approach, so
move on. When rate limited, slow down and come back later.

When anything other than **Try first** works, log it once per distinct problem
with `python3 -m research_control workaround add ...`. A blocked record must
list the approaches tried. The runtime rejects one with fewer than two.
