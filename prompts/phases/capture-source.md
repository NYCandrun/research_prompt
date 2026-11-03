# TASK TYPE: ISOLATED SOURCE CAPTURE

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

If `source capture` fails, work through the playbook sections in this packet:
**Try first**, then **Then try**, then anything else, up to five distinct
approaches. Save whatever works into the assigned source directory and update
the receipt with the method used. When an approach other than the first one
works, log it with `workaround add`.

Only after five approaches fail, record the source as blocked in one call:

```bash
python3 -m research_control source blocked --source-id SOURCE_ID \
  --reason "WHY" --tried "approach -> result" --tried "approach -> result"
```

It writes `BLOCKED.txt` and the receipt. The runtime rejects a blocked record
with fewer than two distinct approaches. Do not edit the canonical source
manifest.
