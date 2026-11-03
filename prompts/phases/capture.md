TASK TYPE: CAPTURE WORK, NOT A STATUS QUESTION

Read `prompts/core/runtime.md` and `prompts/core/evidence.md`, then process only
the immutable source IDs or URLs in the assignment.

For each item, write exactly one terminal disposition: `completed`,
`duplicate`, `excluded`, or `blocked`, with reason and evidence path. A capture
has raw evidence plus the required text or transcript derivative and metadata.
Do not treat an HTTP success or a manifest row alone as capture completion.

Web captures retain URL, capture timestamp, title, method, raw HTML, and text
copy. PDFs retain the original and text with explicit page markers. Transcripts
retain URL, embedding page when relevant, live and upload dates, series,
reliably identified speakers/titles, title source, duration, method, known
caption errors, and timestamps around every 30 to 60 seconds. Preserve
one-word rolling-caption lines.

Find each source as best you can. Use your channel's section of
`RESEARCH_PLAYBOOK.md`: **Try first**, then **Then try**, then anything else
you can think of, up to five distinct approaches per problem. Anything not on
the off-limits list is allowed. An item is `blocked` only after five
approaches fail, and its blocked record lists each approach and its result.

When anything other than **Try first** works, add an entry to your workaround
part with the failure, every approach tried, and exactly what worked. One entry
covers every item the same fix solved.

Write only the assigned manifest part, blocked part, workaround part, evidence
paths, and scratch directory. Never append to the canonical manifest. Return
counts, workaround entry count, and paths only after the local capture
validator passes.
