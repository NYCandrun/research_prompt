TASK TYPE: INDEPENDENT CITATION CLAIM REVIEW

You did not place these citations. Your half of them is in the assigned review
table (`tools/outputs/citation-review-a.md` or `-b.md`), in reading order: each
citation's number, the words before it, its fact IDs, and its source note,
followed by every cited fact's claim, quote, and source. For every citation in
your table, judge whether the fact supports the exact words immediately before
the citation. Judge from the table; open the rendered brief, the fact row, or
the captured source only when the table is not enough (the sentence, cell, or
label context is unclear, or a quote was clipped).

Classify problems as `wrong statement`, `wrong citation`, or `too few
citations`. Recommend the narrowest evidence-faithful fix. Do not infer support
from a real URL alone. Do not edit publication files. Write one row per problem
and explicit assigned/checked/problem counts. Mirror each problem with a stable
finding ID in the assigned `publication-findings-*.jsonl` file. If no problems
exist, write a valid clean record rather than an empty file.

When the assigned packet includes diagrams, also inspect the model registry,
its premise fact/source IDs, captions, and SVG `data-model-id` bindings. Judge
whether each consequential node and edge remains within its D/R evidence class
and whether any H/U relationship is presented as established. Do not treat a
valid model ID or real URL as substantive support by itself.

Write in American English, in spelling and in vocabulary ("program", not "programme"; "job posting", not
"job advert"; "the company is", not "the company are"). Quotes, quoted titles, and names keep the
source's spelling. `work check` lists anything British in what you wrote, and `work succeed` refuses it.
