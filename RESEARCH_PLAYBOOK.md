# Research playbook

This file tells research agents how to get each kind of source. It is meant to
be edited. When a run finds a better way to get something, promote it from
`RESEARCH_WORKAROUNDS.md` into the matching section below.

## Mandate

Find the data as best you can.

For each channel, start with **Try first**. It has worked before. If it fails,
work through **Then try**, then anything else you can think of. Keep going
until something works or you have tried five distinct approaches for that
problem. A distinct approach is a different method, endpoint, tool, URL form,
or source, not the same request again.

Do not stop to judge whether an approach is acceptable. If it is not on the
off-limits list below, it is allowed. Pick the next most promising approach and
run it.

## Off-limits

These are the only approaches not to use:

1. Logging in, or creating or using any account.
2. Paying, or using paywall-removal sites and tricks.
3. Solving or defeating a CAPTCHA or bot challenge page.
4. Rotating IPs or proxies to get around a block.
5. Submitting a form with personal or made-up details, such as a gated-content
   download form.
6. Fetching paths that the live host's `robots.txt` disallows. Archived and
   syndicated copies of those pages are fine.

When a host rate limits you, slow down, move to other work, and come back with
longer spacing. Coordinate pacing for one host in one workflow.

## When a workaround works

If anything other than **Try first** gets the data, write an entry in your
workaround part, `workarounds/<run-date>-<worker-label>.md`. Write one entry per
distinct problem, not one per item. If the same fix worked for 40 videos, say
40.

```markdown
### <YYYY-MM-DD> · <channel> · <short title>

- **Target:** <host, URL pattern, or source IDs>
- **Failure:** <what Try first did: exact error, status code, or symptom>
- **Tried:**
  1. <approach> → <result>
  2. <approach> → <result>
- **Worked:** <exact command, URL pattern, tool, flags, or settings>
- **Items:** <how many items this fixed>
- **Applies to:** <this host only | this platform, e.g. every Wistia embed | general>
- **Playbook change:** <one line: what to add or change in this file>
```

Use the channel names from the section headings below so the merge script can
group entries. The orchestrator runs `python3 tools/merge_workarounds.py` to
rebuild `RESEARCH_WORKAROUNDS.md` from every part.

If all five approaches fail, the item is blocked. Write it to your blocked part
with the same **Failure** and **Tried** lines so the dead ends are visible too.

## Every channel

These work on most hosts. Use them when a channel section runs out.

- Alternate URL forms: `www` and bare domain, trailing slash, `http` to `https`,
  locale prefixes, `?print=1`, `/amp`, and the canonical URL from the page head.
- Data behind the page: `__NEXT_DATA__` or `_next/data/<build>/<path>.json` on
  Next.js sites, `/wp-json/wp/v2/posts` and `/wp-json/wp/v2/pages` on
  WordPress, and JSON calls visible in the browser network log.
- Feeds and indexes: `/feed`, `/rss.xml`, `/atom.xml`, `/sitemap.xml`,
  `/sitemap_index.xml`, and sitemaps listed in `robots.txt`.
- A rendered page: headless Chromium through Playwright for JavaScript-built
  pages, with a normal desktop browser user agent.
- A plain fetch: `curl -L` with a normal browser user agent and `Accept`
  headers when the browser path fails.
- Archived copies: Wayback Machine `id_` snapshots and the Common Crawl index
  at `index.commoncrawl.org`.
- Syndicated copies: the same text on a partner, marketplace, reprint, or
  aggregator page. Grade and attribute the copy you actually captured.
- Other tools: if one parser or downloader fails, try another for the same job.
- Later: retry a failed host at the end of the batch with longer spacing.

## Company website

**Try first:** Read `robots.txt` for sitemap links, then fetch `/sitemap.xml`
and every nested sitemap. Save high-value pages as raw HTML plus a text copy.
Run the media and PDF sweep over every sitemap page.

**Then try:**

1. `/sitemap_index.xml`, `/sitemap-index.xml`, `/page-sitemap.xml`, and
   CMS-specific sitemaps.
2. Crawl the navigation, footer, and docs sidebar when no sitemap exists.
3. Render with headless Chromium when the raw HTML has no body text.
4. Pull page JSON from the framework data endpoint.
5. Capture a recent Wayback snapshot of a page that will not load live.

**Notes from past runs:** none yet.

## PDFs and documents

**Try first:** Download the original. Extract text with `pdftotext -layout`
and mark each page break.

**Then try:**

1. `pdfplumber` or `pypdf` for text, with page numbers from the library.
2. OCR with `ocrmypdf` or `tesseract` when the PDF is scanned images.
3. Gated download forms: look for the direct file URL in the page source, CDN
   links, or a public copy elsewhere.
4. A Wayback copy of the file URL.

**Notes from past runs:** none yet.

## Messaging history

**Try first:** Query Wayback CDX for the homepage and top product pages, one
snapshot per quarter across the lookback:

```text
https://web.archive.org/cdx/search/cdx?url=<url>&output=json&from=<YYYY>&collapse=timestamp:6&filter=statuscode:200
```

Fetch raw HTML from `https://web.archive.org/web/<timestamp>id_/<url>`. Save a
CSV of snapshot date, title, meta description, H1, and H2s.

**Then try:**

1. The availability API: `https://archive.org/wayback/available?url=<url>&timestamp=<YYYYMMDD>`.
2. Spaced, sequential requests after a timeout or 503. Wayback is slow, not
   always blocked.
3. The Common Crawl index for the same URLs and quarters.
4. Variants of the URL, since snapshots are often stored under `www`, a
   trailing slash, or an older path.
5. Dated first-party material: press releases, blog posts, release notes,
   dated PDFs, and video titles and descriptions.

**Notes from past runs:** none yet.

## YouTube

**Try first:** List the channel with `yt-dlp --flat-playlist`. Then fetch
captions and metadata for each long-form video:

```bash
yt-dlp \
  --js-runtimes node \
  --remote-components ejs:npm \
  --extractor-args "youtube:player_client=web_embedded" \
  --skip-download \
  --write-subs \
  --write-auto-subs \
  --sub-langs "en-orig,en" \
  --write-info-json \
  --ignore-errors
```

Space requests about 15 to 30 seconds apart.

**Then try:**

1. Update `yt-dlp` to the latest release and rerun.
2. Other player clients, such as `youtube:player_client=mweb`, `tv`, or
   `web_safari`.
3. Other caption languages, such as `en.*` or the video's original language.
4. The transcript on the embedding company page, if one is published there.
5. Download audio and transcribe it locally (see **No captions**).

**Notes from past runs:** none yet.

## Other video hosts

**Try first:** Open the embedding page and find the player. Fetch the
published caption or transcript file. Pass the embedding page as the referer
when the host requires it.

**Then try:**

1. The player configuration JSON, which usually lists text tracks and media
   URLs. Wistia, Vimeo, Vidyard, Brightcove, and HubSpot all expose one.
2. `yt-dlp` with the embed URL and `--referer <embedding page>`.
3. The oEmbed endpoint for the title, date, and duration.
4. A public copy of the same video on YouTube or the company's other channels.
5. Download audio and transcribe it locally.

**Notes from past runs:** none yet.

## No captions

**Try first:** Download audio only and transcribe with a local Whisper-family
model, such as `faster-whisper` or `whisper.cpp`. Keep timestamps. Delete the
audio afterward unless it is needed as evidence.

**Then try:**

1. A smaller model if the large one runs out of memory or time.
2. Chunk long audio with `ffmpeg` and transcribe the chunks in order.
3. Another local speech-to-text engine that is installed or installable.

**Notes from past runs:** none yet.

## Audio

**Try first:** Read the podcast RSS feed. Save each episode's metadata and any
published transcript.

**Then try:**

1. Feed URLs from the podcast page source, Apple Podcasts lookup
   (`https://itunes.apple.com/lookup?id=<id>&entity=podcastEpisode`), or a
   podcast index.
2. Transcript pages on the podcast's own site.
3. The video version of the episode on YouTube.
4. Download audio and transcribe it locally.

**Notes from past runs:** none yet.

## People

**Try first:** Capture the company's leadership, about, and team pages.
Record names, titles, and dates.

**Then try:**

1. Speaker bios on event, webinar, and conference pages.
2. Bylines and author pages on the company blog.
3. Press releases that announce hires and promotions.
4. Podcast and talk introductions.
5. Wayback snapshots of the team page to date title changes.

**Notes from past runs:** none yet.

## Careers

**Try first:** Find the applicant tracking system from the careers page and
use its public JSON endpoint. Save the raw JSON.

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/<company>?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/<name>?includeCompensation=true`
- Workable: `https://apply.workable.com/api/v1/widget/accounts/<account>`
- SmartRecruiters: `https://api.smartrecruiters.com/v1/companies/<id>/postings`

**Then try:**

1. The board token from the careers page source or the embed script URL.
2. The ATS's public hosted board page, rendered in headless Chromium.
3. The careers page itself, rendered, when jobs are listed inline.
4. Job postings in the company's sitemap.

**Notes from past runs:** none yet.

## Investors

**Try first:** For public companies, use SEC EDGAR filings, earnings call
transcripts, and investor day materials. For private companies, use funding
releases, investor posts, founder interviews, and Form D filings. EDGAR
requires a descriptive `User-Agent` header with a contact address. Use the one
given in `00-inputs/` or chat, and ask once if none is given.

**Then try:**

1. EDGAR full-text search at `https://efts.sec.gov/LATEST/search-index?q=<name>`
   and the company browse JSON at `https://data.sec.gov/submissions/CIK<10 digits>.json`.
2. The investor relations site's own press and events pages.
3. The investor's portfolio page and announcement post.
4. Wire copies of funding releases.

**Notes from past runs:** none yet.

## Press

**Try first:** Capture the company newsroom, blog, and releases across the
lookback.

**Then try:**

1. The newsroom's RSS feed or WordPress JSON.
2. The original wire release on PR Newswire, Business Wire, or GlobeNewswire.
3. An accessible reprint when the original is blocked. Record that the
   original was blocked and grade the reprint as the copy you captured.
4. A Wayback copy of the original release URL.

**Notes from past runs:** none yet.

## Third parties

**Try first:** Capture trade press, analyst pages, review sites, customer and
partner announcements, marketplace listings, procurement records, customer
filings, and competitor pages about the company.

**Then try:**

1. Another review site when one serves a challenge, such as G2, Capterra,
   TrustRadius, Gartner Peer Insights, or a cloud marketplace listing.
2. The customer's or partner's own site for the same announcement.
3. A Wayback copy of the page.
4. A syndicated copy of the article.

**Notes from past runs:** none yet.

## Developer surface

**Try first:** Capture docs, API references, the changelog, the status page,
public GitHub repositories with `git clone`, package registries, SDKs, MCP
servers, and plugins or connectors.

**Then try:**

1. OpenAPI or Swagger files at `/openapi.json`, `/swagger.json`,
   `/api-docs`, or links in the API reference source.
2. The GitHub REST API for repository lists, releases, and tags.
3. Package metadata from npm (`https://registry.npmjs.org/<package>`) or PyPI
   (`https://pypi.org/pypi/<package>/json`), and unpacked package contents.
4. The docs site's search index or sitemap when pages render client side.
5. The status page's JSON API, such as Atlassian Statuspage `/api/v2/summary.json`.

**Notes from past runs:** none yet.

## Competitors

**Try first:** Capture each competitor's website, key product pages, pricing,
docs or knowledge base, press releases, two or three leader talks, review
sites, and two homepage snapshots. Use the same methods as the company
channels above.

**Then try:** the matching company-channel section for whatever failed.

**Notes from past runs:** none yet.

## Tooling

**Try first:** Install a missing tool locally or in a project-local
environment.

**Then try:**

1. Another package manager or a pinned release binary.
2. A Python or Node library that does the same job.
3. The closest tool that is already installed.

Record each substitution in `WORKFLOW_STATE.md`.

**Notes from past runs:** none yet.
