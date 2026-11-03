# Codex execution adapter

Follow `README.md` as the operational entry point: read this file and the
README's sections Run it and Execute task packets. Do not read
`RESEARCH_CONSTITUTION.md` or `WORKFLOW.yaml`: the constitution reaches each
worker inside its brief, and the scheduler reads the workflow. Start a company run with
`python3 -m research_control new --url URL`, then work from inside its
`runs/<slug>/` directory: run `python3 -m research_control run`, dispatch every
ready packet, and repeat until exact-artifact release acceptance passes. Use
subagents for packets marked independent. Give each a unique worker ID, the
packet only, and no inherited status conversation. The SQLite scheduler, not
the parent chat, determines the task graph, retries, dependencies, and
concurrency.

Discovery is one task per channel: the runtime crawls `company_site` and audits
`sitemaps`; each of the other twelve channels gets its own worker. Workers act
only under a held lease; discovery commands refuse to change a channel whose
task is not claimed. To add work to a closed channel, reopen it with
`discovery reopen` and rerun `run`. Runtime-owned work (crawl, sitemap audit,
capture and transcription, reducers) runs inside `run` and is never dispatched.
Concurrency is the orchestrator's call: tune agent dispatch and runtime limits
to whatever is most efficient in the current environment; the configured
numbers are defaults.

Do not ask the user for source, page, batch, or worker counts. Ask the user
only when something is genuinely ambiguous for this company, once, with a
recommendation, while continuing everything that does not depend on the
answer. After the run, read `RESEARCH_WORKAROUNDS.md` in the run directory and
fold what worked into the template's `RESEARCH_PLAYBOOK.md`. Search channels
close as `sufficient` against the numbered research questions in `00-scope.md`
or as `saturated`; triage bounds extraction by the same questions. Numeric
limits are safety breakers and must produce incomplete status when reached.

`run` saves the run to its `run-data/<slug>` branch and confirms the push
before every phase check, at every phase start, and at the end. A fresh
template checkout continues a run with `python3 -m research_control resume
--url URL`, then `run` inside `runs/<slug>`.

Do not skip a failed control, edit scheduler state directly, or claim completion
without a passing release manifest. When repository instructions and a packet
conflict, block that packet and report the conflict; unrelated ready work may
continue. Framework changes during a run go into the template first and reach
the run through `sync-engine`, which records them in the run history.

## Running the orchestrator

Measured on the Tribe AI run (3,051 orchestrator turns): four fifths of the
orchestrator's cost was context re-read on every turn and thinking on
mechanical turns, not the model. The judgment moments are what the
orchestrator is for: a worker's result is thin or wrong, a check fails for a
reason the report does not spell out, an evidence call has to be made (for
example whether internal files on an employee's personal account count, and
how to label them). Keep the model for those and cut everything else.

- Model and effort: run the orchestrator on the `strong` tier (Claude Opus
  5.5) at `high` effort. The effort setting applies to every turn and cannot
  be raised only for the judgment moments, and those are where a shallower
  read costs the most: a vaguer correction on a relaunch, a misread check
  report, a weaker evidence call. High effort wastes some thinking on dispatch
  turns; that waste is small next to context size and turn count, which the
  rules below cut. Treat `medium` effort, and the `standard` tier, as
  experiments: after a run on high has set a baseline (intervention count,
  what the reviews found), change one of them on a later run and compare.
- Context: compact at the start of every phase. Keep diagnostic output out of
  the conversation: read `run`'s short summary, open `run --full` only when the
  summary is not enough, and never paste a brief, a capture, or a fact store.
  When a problem needs reading large output to diagnose, hand it to one
  subagent on the `strong` tier with the failure report and act on its short
  answer. A worker's report is the thing to read; open its output only to
  decide a relaunch.
- Turns: launch every entry in `start_workers` in one turn, wait for the
  completion notifications instead of polling, then rerun `run` once. About
  three orchestrator turns per wave of workers is the target; the Tribe run
  took twelve.
- Going again: when a result is thin or wrong, say in one line what was wrong
  and what the next attempt does differently, then relaunch with that line
  added to the worker's prompt after `Read <read> in full and follow it.`
  Reopen a channel, add a question, or record an edit through the commands;
  never fix a worker's output by hand.
- Framework changes: fix the template between runs. Mid-run, change it only
  when the run cannot proceed, then `sync-engine`; a run is not the place to
  develop the runtime.
