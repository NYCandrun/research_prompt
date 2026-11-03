# Research playbook

This file tells research workers how to get each kind of source. Edit it as
runs teach you things. The packet writer copies the relevant sections into
each worker's task packet, so workers never read this file directly.

Section headings end with the channel keys they cover, in parentheses. The
packet writer matches on those keys. Keep them when you rename a section.

## Mandate

Find the data as best you can.

For each problem, start with **Try first**. It has worked before. If it fails,
work through **Then try**, then anything else you can think of. Keep going
until something works or five distinct approaches for that problem have
failed. A distinct approach is a different method, endpoint, tool, URL form,
or source, not the same request again.

A problem is one failure mode, not one item. If 40 videos fail the same way,
find one fix and apply it to all 40.

Do not stop to judge whether an approach is acceptable. If it is not on the
off-limits list, it is allowed. Pick the next most promising approach and run
it.

## Off-limits

These are the only approaches not to use:

1. Logging in, or creating or using any account.
2. Paying, or using paywall-removal sites and tricks.
3. Fetching paths that the live host's `robots.txt` disallows. Archived and
   syndicated copies of those pages are fine.

Two definitions, not rules: a CAPTCHA or bot-challenge page counts as a failed
approach, so move to the next one instead of trying to solve it. A rate limit
means slow down, do other work, and come back with longer spacing.

## Workaround log

When anything other than **Try first** gets the data, record it in one call:

```bash
python3 -m research_control workaround add \
  --task TASK_ID --channel CHANNEL_KEY --target "host, URL pattern, or source IDs" \
  --failure "what Try first did: exact error, status code, or symptom" \
  --tried "approach -> result" --tried "approach -> result" \
  --worked "exact command, URL pattern, tool, flags, or settings" \
  --items 40 --applies platform --playbook-change "one line"
```

One entry per distinct problem. `--applies` is `host`, `platform` (every
Wistia embed, every Greenhouse board), or `general`. The orchestrator's `run`
command rebuilds `RESEARCH_WORKAROUNDS.md` from these entries for review.

When five approaches fail, the item is blocked. Blocked records must list the
approaches tried: `discovery close --state blocked --tried ...` for a channel,
`source blocked --tried ...` for a source. The runtime rejects a blocked record
with fewer than two distinct approaches.

## Every channel (general)

These work on most hosts. Use them when a channel section runs out.

- Alternate URL forms: `www` and bare domain, trailing slash, `http` to
  `https`, locale prefixes, `?print=1`, `/amp`, and the canonical URL from the
  page head.
- Data behind the page: `__NEXT_DATA__` or `_next/data/<build>/<path>.json`
  on Next.js sites, `/wp-json/wp/v2/posts` and `/wp-json/wp/v2/pages` on
  WordPress, and JSON calls visible in the browser network log.
- Feeds and indexes: `/feed`, `/rss.xml`, `/atom.xml`, `/sitemap.xml`,
  `/sitemap_index.xml`, and sitemaps listed in `robots.txt`.
- A rendered page: headless Chromium through Playwright for JavaScript-built
  pages, with a normal desktop browser user agent.
- A plain fetch: `curl -L` with a normal browser user agent and `Accept`
  headers when the browser path fails, or the reverse.
- Archived copies: Wayback Machine `id_` snapshots and the Common Crawl index
  at `index.commoncrawl.org`.
- Syndicated copies: the same text on a partner, marketplace, reprint, or
  aggregator page. Grade and attribute the copy you actually captured.
- Other tools: if one parser or downloader fails, try another for the same
  job.
- Later: retry a failed host at the end of the batch with longer spacing.

## Company site and sitemaps (company_site, sitemaps)

**Try first:** `python3 -m research_control discovery crawl` for discovery,
and `python3 -m research_control source capture --source-id ID` for an
ordinary page. Read `robots.txt` for sitemap links, then `/sitemap.xml` and
every nested sitemap.

**Then try:**

1. `/sitemap_index.xml`, `/sitemap-index.xml`, `/page-sitemap.xml`, and
   CMS-specific sitemaps.
2. Crawl the navigation, footer, and docs sidebar when no sitemap exists.
3. Render with headless Chromium when the raw HTML has no body text.
4. Pull page JSON from the framework data endpoint.
5. Capture a recent Wayback snapshot of a page that will not load live.

**Notes from past runs:** none yet.

## Newsroom, blog, and press (newsroom_blog)

**Try first:** Capture the newsroom, blog, and releases across the lookback
from the site's own listing pages.

**Then try:**

1. The newsroom's RSS feed or WordPress JSON.
2. The original wire release on PR Newswire, Business Wire, or GlobeNewswire.
3. An accessible reprint when the original is blocked. Record that the
   original was blocked and grade the reprint as the copy you captured.
4. A Wayback copy of the original release URL.

**Notes from past runs:** none yet.

## Docs, help, and developer surface (docs_help, code_packages)

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
5. The status page's JSON API, such as Atlassian Statuspage
   `/api/v2/summary.json`.

**Notes from past runs:** none yet.

## Careers (careers)

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

## Video (video)

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
4. For embedded players (Wistia, Vimeo, Vidyard, Brightcove, HubSpot): the
   player configuration JSON, which lists text tracks and media URLs, or
   `yt-dlp` with the embed URL and `--referer <embedding page>`.
5. The transcript on the embedding company page, or a public copy of the
   same video on another channel.
6. Download audio and transcribe it locally (see **Transcription**).

**Notes from past runs:** none yet.

## Podcasts (podcasts)

**Try first:** Read the podcast RSS feed. Save each episode's metadata and
any published transcript.

**Then try:**

1. Feed URLs from the podcast page source, Apple Podcasts lookup
   (`https://itunes.apple.com/lookup?id=<id>&entity=podcastEpisode`), or a
   podcast index.
2. Transcript pages on the podcast's own site.
3. The video version of the episode on YouTube.
4. Download audio and transcribe it locally (see **Transcription**).

**Notes from past runs:** none yet.

## Transcription (transcription)

**Try first:** Download audio only and transcribe with a local Whisper-family
model, such as `faster-whisper` or `whisper.cpp`. Keep timestamps. Delete the
audio afterward unless it is needed as evidence.

**Then try:**

1. A smaller model if the large one runs out of memory or time.
2. Chunk long audio with `ffmpeg` and transcribe the chunks in order.
3. Another local speech-to-text engine that is installed or installable.

**Notes from past runs:** none yet.

## Social (social)

**Try first:** Capture the company's own account pages and the posts linked
from its site. Many social hosts block anonymous reads, so expect to fall
back quickly.

**Then try:**

1. The same announcement on the company blog or newsroom.
2. Syndicated copies on press or aggregator sites.
3. A Wayback snapshot of the post URL.
4. An RSS or JSON feed where the host offers one, such as Mastodon or Bluesky.

If the host serves a login wall, that is a blocked surface. Record it and
move on.

**Notes from past runs:** none yet.

## Independent web (independent_web)

**Try first:** Capture trade press, analyst pages, review sites, customer and
partner announcements, marketplace listings, procurement records, customer
filings, and competitor pages about the company.

**Then try:**

1. Another review site when one serves a challenge, such as G2, Capterra,
   TrustRadius, Gartner Peer Insights, or a cloud marketplace listing.
2. The customer's or partner's own site for the same announcement.
3. A Wayback copy of the page.
4. A syndicated copy of the article.
5. For public companies, SEC EDGAR full-text search
   (`https://efts.sec.gov/LATEST/search-index?q=<name>`) with a descriptive
   `User-Agent` header.

**Notes from past runs:** none yet.

## Messaging history and archives (archives)

**Try first:** Query Wayback CDX for the homepage and top product pages, one
snapshot per quarter across the lookback:

```text
https://web.archive.org/cdx/search/cdx?url=<url>&output=json&from=<YYYY>&collapse=timestamp:6&filter=statuscode:200
```

Fetch raw HTML from `https://web.archive.org/web/<timestamp>id_/<url>`.

**Then try:**

1. The availability API:
   `https://archive.org/wayback/available?url=<url>&timestamp=<YYYYMMDD>`.
2. Spaced, sequential requests after a timeout or 503. Wayback is slow, not
   always blocked.
3. The Common Crawl index for the same URLs and quarters.
4. Variants of the URL, since snapshots are often stored under `www`, a
   trailing slash, or an older path.
5. Dated first-party material: press releases, blog posts, release notes,
   dated PDFs, and video titles and descriptions.

**Notes from past runs:** none yet.

## PDFs and documents (pdf)

**Try first:** Download the original. Extract text with `pdftotext -layout`
and mark each page break.

**Then try:**

1. `pdfplumber` or `pypdf` for text, with page numbers from the library.
2. OCR with `ocrmypdf` or `tesseract` when the PDF is scanned images.
3. Gated download forms: look for the direct file URL in the page source, CDN
   links, or a public copy elsewhere.
4. A Wayback copy of the file URL.

**Notes from past runs:** none yet.

## Tooling (tooling)

**Try first:** Install a missing tool locally or in a project-local
environment.

**Then try:**

1. Another package manager or a pinned release binary.
2. A Python or Node library that does the same job.
3. The closest tool that is already installed.

Record each substitution in `WORKFLOW_STATE.md`.

**Notes from past runs:** none yet.
