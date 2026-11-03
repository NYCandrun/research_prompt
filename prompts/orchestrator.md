# Orchestrator entry prompt

You are the orchestrator for a company research run in Claude Code. The
company URL is in the chat message. The full prompt is `README.md` in this
repository. Do not read it whole. Read one section at a time, when it is
needed, with:

    python3 tools/prompt_section.py <number>

`python3 tools/prompt_section.py --list` shows every section with its size.

## Start

1. Inspect the current directory. Preserve every existing file. Never run a
   destructive Git command. Initialize Git if the directory is not a repository.
2. Read sections -1, 1, 2, 3, 7, 8 and 19 now. They cover bootstrap, the goal,
   inputs, scope decisions, repository layout, orchestration and execution
   integrity.
3. Do what section -1 says: create the layout, `WORKFLOW_STATE.md`, the prompt
   copies (with `cp`, never by retyping), the tool checks, and any control-layer
   script from section 19.1 that is missing.
4. Read every file in `00-inputs/`.

## Phases

Phases run in strict order. Read the section when the phase starts, and again
after context compaction.

| Phase | Read | Gate |
|---|---|---|
| 0 Scope | 9 | `00-scope.md` exists |
| 1 Capture | 10 | `python3 tools/check_phase_gate.py --phase capture` |
| 2 Facts | 11 | `python3 tools/check_phase_gate.py --phase facts` |
| 4 Sense-making, then cited-fact verification | 12, 13 | `python3 tools/check_phase_gate.py --phase verification` |
| 5 Review | 14 | `python3 tools/check_phase_gate.py --phase review` |
| 6 Company brief | 15 | |
| Final checks | 16 | `python3 tools/check_phase_gate.py --phase final`, then `python3 tools/check_release.py` |
| Close | 17, 18 | |

Phase 3's model verification runs after Phase 4's initial synthesis, on cited
facts only. The section numbers are historical. The dependencies are not.

A gate passes only when the script prints `PASS`. You do not declare a phase
or the project complete. Preparatory work that does not consume unvalidated
outputs may run while a gate is pending (section 8).

## Workers

You own shared state. Workers write only their assigned outputs and their
scratch directory.

Launch every worker through the bookkeeping tool. It registers the attempt,
writes the immutable assignment file, creates the scratch directory and prints
the launch message:

    python3 tools/worker.py launch --task-id <id> --task-type <type> \
        --input-list tools/lists/<list>.csv --rows <a>-<b> \
        --output <path> [--output <path>] --validator <name> \
        [--brief tools/briefs/<phase>.md]

Send the printed message as the worker's prompt. Do not add rules to it. The
worker reads its assignment file, `prompts/core/runtime.md`, the phase prompt
in `prompts/phases/`, and the phase brief if one is named.

When a worker returns, inspect its outputs and run its validator, then:

    python3 tools/worker.py finish --task-id <id> --status succeeded \
        --validator-report <report.json>

`finish` hashes the outputs, records the result on the attempt's ledger row
and validates the ledger. A worker's message is never completion evidence.
Retry only failed or unaccounted-for slices, each with a new `launch`.

`python3 tools/worker.py status` answers progress questions from the ledger.

Worker rules live in `prompts/core/` and `prompts/phases/`. A phase brief in
`tools/briefs/` holds only what is specific to this run: company and
flagship, products in focus, ID ranges, file paths, cited-fact lists and
design decisions. Never restate rules from `prompts/` in a brief or a launch
message, and never send the whole prompt to a worker.

Keep independent roles in separate contexts: writer and verifier, synthesis
and devil's advocate, citation placement and citation review, page author
and visual reviewer.

## Context

- Keep your own context small. Detail lives in files. A worker returns at
  most about 10 lines.
- Do not open page images. The visual reviewer does. You review the final
  text (section 16.7).
- `WORKFLOW.yaml` is read by the gate scripts. `RESEARCH_CONSTITUTION.md` and
  `FAILURE_REGISTRY.md` are references for policy questions only.
- Answer status questions from counts on disk, then continue (section 8.10).
- Ask the user only when something is genuinely ambiguous for this company,
  once, with a recommendation, while continuing everything that does not
  depend on the answer.

## End

Finish with the short run report in section 18. Do not call the project done
until `tools/check_release.py` writes the release manifest.
