# Instructions: start a research run from a message

You are the control agent for this repository. The user's message names one or
more company domains (a URL, or a bare domain such as `ideo.com`) and says
"read instructions.md". Everything below is what happens next. Open the session
on Claude Opus 5.5 at high effort; the model and effort for each worker you
start come from the routing table in `CLAUDE.md`.

Read `CLAUDE.md` in full first. It holds the operating rules: how to start
workers, how many turns a wave should take, what to keep out of your
conversation, when to ask the user, and how the run saves itself. Then read the
README sections it names (Run it, Execute task packets, How many workers,
Talking to the user). Do not read `RESEARCH_CONSTITUTION.md` or
`WORKFLOW.yaml`.

## 1. Check the checkout

```bash
python3 -m research_control preflight
git remote get-url origin
```

Preflight checks the template and the local runtime. The origin remote is where
every run saves itself (a `run-data/<slug>` branch), so the session needs push
access to it. When there is no remote or no push access, say so once and
continue; the run still works, and nothing is saved off this machine.

The tools a run needs are installed by `start` itself before anything else:
yt-dlp, ffmpeg, and faster-whisper for recordings, with the Whisper and
speaker-label models downloaded ahead of time; poppler for PDFs; Node with
Playwright and its Chromium for the headless browser and PDF printing. The
result's `tools` entry says what was already present, what was installed, and
what could not be (with the reason). A tool that could not be installed never
stops the run: the capture method falls back and preflight warns. Retry by
hand with `python3 -m research_control setup`, or install the named package
the way the reason says; do not spend turns on a tool the environment cannot
have.

## 2. Start from the domains in the message

```bash
python3 -m research_control start --url DOMAIN [--url DOMAIN ...]
```

One domain: the run starts at once, and the result names its directory
(`runs/<slug>`) and the next command. Several domains on one domain name
(`www.ideo.com` and `designkit.ideo.com`) count as one.

Several domains: the runtime reads each homepage and writes one brief under
`runs/_grouping/<id>/`. The result lists one worker under `start_workers`; start
it on the `standard` tier (Claude Sonnet 5.5, medium effort) with the one-line
prompt `Read <read> in full and follow it.` It decides which domains belong to
one company (IDEO and IDEO U are one; a parent and a subsidiary with its own
name and products are two) and writes `decision.json`. When it reports back:

- If its confidence is `clear`, run `python3 -m research_control start --apply <id>`.
  That starts one run per company. A company's extra domains become
  first-party domains of its run: crawled, graded as the company's own words,
  filed by path like its main site.
- If its confidence is `unsure`, ask the user the worker's one question, with
  the worker's recommendation, once. Edit `decision.json` to match the answer
  (groups, confidence `clear`), check it with
  `python3 -m research_control start --validate <id>`, then apply it.

`start --apply` prints each run's directory and next command. A run that
already exists for a domain is left as it is and reported as `exists`;
continue it instead of starting over.

## 3. Drive every run to release

For each run, work from inside its directory and follow `CLAUDE.md`:

```bash
cd runs/<slug>
python3 -m research_control run
```

Start every entry in `start_workers` in one turn, each with the model and
effort for its `model_level`, wait for the completion notifications, rerun
`run` once, and repeat until it reports `release_ready`; then run
`python3 -m research_control release`. Do not stop at a plan, a packet list, a
draft, or a progress summary.

Several companies are several separate runs: each has its own directory,
scheduler, saves, and worker waves, and nothing is shared between them. Drive
them side by side: start each run's workers as its own wave, keep each wave's
results with its run, and name the company in every message to the user. A
long `run` (capture with transcription) in one directory never blocks another
run's `run`. When a machine can only hold one run at a time, finish one before
the next; each saves itself, and `python3 -m research_control resume --url URL`
continues any of them from a fresh checkout.

If the scope worker or you find another domain a company itself publishes on,
add it from inside that run's directory with
`python3 -m research_control scope add-host --url URL --reason "..."` and rerun
`run`.

## 4. Finish

When a run is released, read its `RESEARCH_WORKAROUNDS.md` and fold what worked
into the template's `RESEARCH_PLAYBOOK.md`; commit that to the template's main
branch. Then report in plain English, one section per company: what the report
covers, which source channels closed as sufficient or saturated, what was
blocked and what the alternate-copies pass found, and where the report and the
`run-data/<slug>` branch are.

Ask the user only when something is genuinely ambiguous for a company, once,
with a recommendation, while continuing everything that does not depend on the
answer.
