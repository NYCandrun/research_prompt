# Claude Code execution adapter

## Talking to the user

Write for the user in plain English. Leave out jargon and internal shorthand ("shard", "slice", "packet", "gate", "reconcile", "the X repo"): say what a thing is ("a batch of 48 facts to verify", "a chunk of a source's text", "the phase checks"), name a repository by its GitHub name (owner/repository, for example carlmueller-tribe/mori), and name a source by what it is (a podcast episode, a company blog post), not only by its ID. This holds for every message to the user, status updates included,
and for anything a worker reports that you pass on.

Follow `README.md` as the operational entry point: read this file and the
README's sections Run it, Execute task packets, How many workers, and Talking
to the user. Do not read `RESEARCH_CONSTITUTION.md` or `WORKFLOW.yaml`: the
constitution reaches each worker inside its brief, and the scheduler reads the
workflow. `instructions.md` is the entry point when the user's message names
the domains: `python3 -m research_control start --url URL` (one `--url` per
domain) starts one company's run at once and, for several domains, has a
worker decide which belong to one company before starting one run per company.
Then work from inside each `runs/<slug>/` directory: rerun
`python3 -m research_control run` and dispatch every ready packet until
exact-artifact release passes.

- `run` prints a short summary; the full result is in
  `tools/outputs/last-run.json` (`run --full` prints it). Start one subagent
  per entry in `start_workers`, with the model and effort for its
  `model_level` from the table below, and give it a one-line prompt:
  `Read <read> in full and follow it.` The file it names holds everything the
  worker needs: its worker ID, lifecycle commands, run notes, the
  `work check` it runs before it succeeds, the task's instructions (only the
  rules that task uses), and the text of the files it reads. Never paste a
  brief into the prompt: it would stay in your conversation and be re-read on
  every later step. Separate workers run work that reads different material
  in parallel; tasks that read the same files share one worker, so nothing is
  read twice; reviews whose value is independent judgment always get their
  own worker. Do not split one task's reading across workers or add workers
  beyond these entries. When a worker reports something for you, act on it; a
  small correction to a finished output is recorded with `work record-edit`.
  Discovery is one task per channel: the runtime handles `company_site` and
  `sitemaps`; each of the other twelve channels gets its own worker.
- Workers act only under a held lease: `work start` claims and starts the
  task; succeed only after outputs exist. Never let a worker run discovery or capture
  commands for a task it has not claimed. To add work to a closed channel,
  reopen it with `discovery reopen` and rerun `run` so the scheduler re-queues
  the task.
- Blocked captures are not the end of the line: the scheduler plans an
  alternate-copies pass once page captures finish (and a later pass for anything
  blocked after it), and its worker records a public copy of the same content,
  or that none exists, for every blocked source in its list.
- Ask the user only when something is genuinely ambiguous for this company,
  once, with a recommendation, while continuing everything that does not
  depend on the answer.
- A company with more than one domain of its own (IDEO and IDEO U) is one run:
  `start` groups the domains by company, or name them yourself with
  `new --url URL --also URL`, one `--also` per extra domain, or add a domain
  mid-run with `scope add-host --url URL --reason "..."` and rerun `run`. Every
  first-party domain is crawled and graded as the company's own words. Several
  companies are several separate runs, each driven from its own directory.
- After the run, read `RESEARCH_WORKAROUNDS.md` in the run directory and fold
  what worked into the template's `RESEARCH_PLAYBOOK.md`.
- Do not invent source, page, batch, or worker quotas. Discovery channels close
  as `sufficient` against the numbered research questions or as `saturated`;
  triage then bounds extraction by those questions.
- Runtime-owned work (crawl, sitemap audit, capture and transcription,
  reducers, filing, digests) runs inside `run`; never hand it to an agent. Use `run --plan-only`
  while another `run` process is executing.
- Scripted work (crawling, capture, transcription, history, reducers) sizes its
  own parallelism to the machine's cores and memory; raise or lower it with the
  README's overrides only when the environment shows strain or slack.
- Concurrency is your call. Dispatch as many ready agent packets at once, and
  set runtime and scheduler limits to whatever finishes fastest without
  failures in the environment you are in (cores, memory, network, rate limits
  you hit). The configured numbers are defaults; see README for the overrides.
- Preserve single-writer reducer ownership, record concrete access blockers,
  and never edit scheduler state directly.
- The control agent's conversation is kept with the run: every save to
  GitHub adds what it gained since the last save to
  `08-control agent conversation history/` (secrets removed), and `run`
  saves, pushes, and confirms the push at the start of every phase. At the end
  of the run it is written as one file, checked by script against every
  earlier part, and the parts are deleted. Only write it, by those scripts;
  never read or review it unless the user asks. Questions after the run are
  not added.
- Keep the evidence. A run folder is ignored by the template's git. `run`
  saves the run to the remote's `run-data/<slug>` branch and confirms the
  push before every phase check, at every phase start, and at the end
  (captures, HTML, transcripts, facts, drafts, the scheduler snapshot, a git
  bundle of every cloned repository, and this conversation). Run
  `python3 -m research_control --root runs/<slug> archive` by hand only for a
  save between those points, such as after a long wave of workers. Never
  delete captures or transcripts after extraction; reuse them instead of
  capturing again.
- Work from the remote. If this machine is lost, a fresh template checkout
  continues the run: `python3 -m research_control resume --url URL`, then
  `run` from inside `runs/<slug>`. It restores the run and the scheduler from
  the branch, syncs the engine, and releases the old machine's leases.
- When the framework changes mid-run, change the template, commit, and run
  `python3 -m research_control --root runs/<slug> sync-engine` from the template
  checkout so the change is recorded in the run history.

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

## Side runs

New sources that arrive after fact drafting (a later search) do not go back
through the main run. Hold them (`limits --extraction-budget 1`), finish the
run, then take them through a side run (`side new`, `side file`,
`side verify`, `side render`, `side merge`; see README) with one worker per
brief it prints. Its merge records every change, so nothing finished reruns.

## American English

Everything written into a run is in American English, in spelling and in
vocabulary: what workers draft (facts, synthesis, reviews, the brand guide,
the report, diagrams) and what you write yourself (scope questions, notes,
recorded edits and their reasons). `scope add-question`, `scope record-edit`,
and `work record-edit` refuse British spellings and terms, as `work succeed`
does for workers. Quotes, quoted titles, and names keep the source's spelling.

## Model routing

Every packet names an advisory tier (`model_route` in its JSON and in the
`run` output). Extraction batches carry their own tier by the kind of source
they read: code, specs, data, and pages on `standard`; recordings and business
records on `strong`. Claude Code can
select a model and effort per subagent, so apply the route on every dispatch:

| Tier | Model class | Subagent model | Effort | Task types |
|---|---|---|---|---|
| `frontier` | `strongest_available` | `fable` (Claude Fable 5.1) | `high` | findings and report plan, cited-fact verification, devil's-advocate review, diagram modeling |
| `strong` | `flagship_capable` | `opus` (Claude Opus 5.5) | `high` | every task type not listed in another tier |
| `standard` | `balanced_capable` | `sonnet` (Claude Sonnet 5.5) | `medium` | discovery, triage, re-triage, filing spot check, language review |
| `economy` | `faster_capable` | `haiku` (Claude Haiku 5.5) | `low` | assembler |

Pass the tier's model and effort when launching the worker, and have the worker
record them on completion with
`work succeed TASK_ID --worker-id ID --model MODEL_ID --effort EFFORT`, using the
full model ID (`claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`). If
the host refuses a model, fall back to the available model and record the model
that actually ran; routing never blocks a task or relaxes a gate.
