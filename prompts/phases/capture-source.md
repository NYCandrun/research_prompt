# TASK TYPE: ISOLATED SOURCE CAPTURE

The runtime executes this deterministic task itself inside `python3 -m research_control run`; it is not dispatched to an agent. This text documents the contract it enforces.

Capture only the source in the immutable task input. Write only its
`01-sources/captures/SOURCE_ID/` directory and private capture receipt.

The `source capture` command automatically reuses an identical response already
stored by research or brand discovery. Cache reuse changes only transport; this
packet must still create its own canonical capture, receipt, and evidence
disposition.

For an ordinary public page, run:

```bash
python3 -m research_control source capture --source-id SOURCE_ID
```

For JavaScript-rendered pages, PDFs, video, podcasts, feeds, repositories, or
other formats, use the runtime's appropriate public-access tool. Preserve the
original file and create a canonical UTF-8 text derivative with stable location
markers. Update the generated receipt only with observed metadata; set
`canonical_text_ready` to true and `status` to `captured` only after that
derivative exists.

The runtime's chain is the playbook's first approach for a page: a plain
request with retries, then the headless browser. When both fail, it creates
the assigned source directory with a nonempty `BLOCKED.txt` and a receipt
with `status: blocked`, the concrete failure, the access method, and the
evidence. A blocked source then goes to the alternate-copies pass, where a
worker works the rest of the playbook before recording that no public copy
exists. Nothing edits the canonical source manifest except the capture
reducer.
