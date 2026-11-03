# Research playbook

This file tells research workers how to get each kind of source. Edit it as
runs teach you things: `RESEARCH_WORKAROUNDS.md`, written by each run, lists
what workers had to do differently and what worked. Fold the entries worth
keeping into the matching section here.

Workers never read this file. The packet writer copies the general sections
plus the sections for the worker's channels into its brief. Section headings
end with the channel keys they cover, in parentheses. Keep the keys when you
rename a section.

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

1. Logging in, or creating or using any account. Login-walled platforms
   (LinkedIn, X, Facebook, Instagram, Threads, TikTok) are recorded as leads
   and read through public copies.
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
Wistia embed, every Greenhouse board), or `general`. `run` rebuilds
`RESEARCH_WORKAROUNDS.md` from these entries for review after the run.

When five approaches fail, the item is blocked, and the record must list the
approaches: `discovery close --state blocked --tried ...` for a channel, and
`discovery alternate --none --tried ...` for a source whose public copy you
could not find. The runtime rejects either with fewer than two distinct
approaches.

## Every channel (general)

These work on most hosts. Use them when a channel section runs out.

- The runtime's own chain is the first approach for a page: a plain request
  with retries, then the headless browser. `python3 -m research_control web
  render --url URL` opens any page as desktop Chrome and prints its text and
  links. `web fetch --url URL` reports the HTTP status of a candidate copy.
- Alternate URL forms: `www` and bare domain, trailing slash, `http` to
  `https`, locale prefixes, `?print=1`, `/amp`, and the canonical URL from the
  page head.
- Data behind the page: `__NEXT_DATA__` or `_next/data/<build>/<path>.json`
  on Next.js sites, `/wp-json/wp/v2/posts` and `/wp-json/wp/v2/pages` on
  WordPress, and JSON calls visible in the browser network log.
- Feeds and indexes: `/feed`, `/rss.xml`, `/atom.xml`, `/sitemap.xml`,
  `/sitemap_index.xml`, and sitemaps listed in `robots.txt`.
- Archived copies: Wayback Machine `id_` snapshots, the Common Crawl index at
  `index.commoncrawl.org`, Software Heritage for repositories, and GH Archive
  for GitHub events (the discovery instructions give the routes).
- Syndicated copies: the same text on a wire service, the issuer's own
  newsroom, a partner, a marketplace, a reprint, or an aggregator. Grade and
  attribute the copy you actually captured.
- Other tools: if one parser or downloader fails, try another for the same
  job.
- Later: retry a failed host at the end of the batch with longer spacing.

## Company site and sitemaps (company_site, sitemaps)

**Try first:** The runtime crawls the company host and audits its sitemaps.
For a page the crawl could not read, `web render --url URL`.

**Then try:**

1. `/sitemap_index.xml`, `/sitemap-index.xml`, `/page-sitemap.xml`, and
   CMS-specific sitemaps, admitted with `discovery add`.
2. The navigation, footer, and docs sidebar when no sitemap exists.
3. Page JSON from the framework data endpoint.
4. A recent Wayback snapshot of a page that will not load live.

**Notes from past runs:** none yet.

## Newsroom, blog, and press (newsroom_blog)

**Try first:** The newsroom, blog, and release listing pages across the
lookback.

**Then try:**

1. The newsroom's RSS feed or WordPress JSON.
2. The original wire release on PR Newswire, Business Wire, or GlobeNewswire.
3. An accessible reprint when the original is blocked. Record that the
   original was blocked and grade the reprint as the copy you captured.
4. A Wayback copy of the original release URL.

**Notes from past runs:** none yet.

## Docs, help, and public code (docs_help, code_packages)

**Try first:** Docs, API references, the changelog, the status page, the
company's GitHub organizations, package registries, SDKs, MCP servers, and
plugins or connectors. The discovery instructions give the GitHub routes.

**Then try:**

1. OpenAPI or Swagger files at `/openapi.json`, `/swagger.json`,
   `/api-docs`, or links in the API reference source.
2. `llms.txt` and `llms-full.txt` on docs hosts, which carry the whole docs
   text in one file.
3. Package metadata from npm (`https://registry.npmjs.org/<package>`) or PyPI
   (`https://pypi.org/pypi/<package>/json`), and unpacked package contents.
4. The docs site's search index or sitemap when pages render client side.
5. The status page's JSON API, such as Atlassian Statuspage
   `/api/v2/summary.json`.

**Notes from past runs:** none yet.

## Careers (careers)

**Try first:** Find the applicant tracking system from the careers page and
use its public JSON endpoint.

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/<company>?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/<name>?includeCompensation=true`
- Workable: `https://apply.workable.com/api/v1/widget/accounts/<account>`
- SmartRecruiters: `https://api.smartrecruiters.com/v1/companies/<id>/postings`

**Then try:**

1. The board token from the careers page source or the embed script URL.
2. The ATS's public hosted board page, rendered in the headless browser.
3. The careers page itself, rendered, when jobs are listed inline.
4. Job postings in the company's sitemap.

**Notes from past runs:** none yet.

## Video (video)

**Try first:** List the channel with `yt-dlp --flat-playlist`. The runtime
transcribes admitted videos from captions or audio. For captions by hand:

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

**Try first:** The podcast RSS feed, for each episode's metadata, audio
enclosure, and any published transcript.

**Then try:**

1. Feed URLs from the podcast page source, Apple Podcasts lookup
   (`https://itunes.apple.com/lookup?id=<id>&entity=podcastEpisode`), or a
   podcast index.
2. Transcript pages on the podcast's own site.
3. The video version of the episode on YouTube.
4. Download audio and transcribe it locally (see **Transcription**).

**Notes from past runs:** none yet.

## Transcription (transcription)

**Try first:** The runtime transcribes from captions, then from audio with
Whisper. By hand: audio only, a local Whisper-family model such as
`faster-whisper` or `whisper.cpp`, timestamps kept, audio deleted afterward
unless it is needed as evidence.

**Then try:**

1. A smaller model if the large one runs out of memory or time.
2. Chunk long audio with `ffmpeg` and transcribe the chunks in order.
3. Another local speech-to-text engine that is installed or installable.

**Notes from past runs:** none yet.

## Social (social)

**Try first:** The company's own account pages and the posts linked from its
site. Login-walled hosts are recorded as leads, so expect to fall back
quickly.

**Then try:**

1. The same announcement on the company blog or newsroom.
2. Syndicated copies on press or aggregator sites.
3. A Wayback snapshot of the post URL.
4. An RSS or JSON feed where the host offers one, such as Mastodon or Bluesky.

**Notes from past runs:** none yet.

## Independent web (independent_web)

**Try first:** Trade press, analyst pages, review sites, customer and partner
announcements, marketplace listings, procurement records, customer filings,
and competitor pages about the company.

**Then try:**

1. Another review site when one serves a challenge, such as G2, Capterra,
   TrustRadius, Gartner Peer Insights, or a cloud marketplace listing.
2. The customer's or partner's own site for the same announcement.
3. A Wayback copy of the page.
4. A syndicated copy of the article.

**Notes from past runs:** none yet.

## Market and competitors (market_competitors)

**Try first:** Register each competitor as you find it, then admit its pages
with the subject tag so the facts are filed against it:

```bash
python3 -m research_control discovery competitor --name "Acme" --url https://acme.example \
  --kind direct --reason "same offering to the same buyers; named on the company's comparison page"
python3 -m research_control discovery add --channel market_competitors --subject acme \
  --url https://acme.example/pricing --evidence "pricing page"
```

For each direct competitor, more lightly than the company itself: the
website and key product pages, pricing and packaging, the docs or knowledge
base for the competing product only (about 400 pages at most; name what was
left out in the evidence), press releases over the lookback, two or three
leader talks when useful, review sites and marketplace listings, two
homepage snapshots from the archives (one recent, one at the start of the
lookback), and the competitor's own pages about the company being
researched. The discovery instructions give the GitHub routes.

**Then try:** the matching channel section above for whatever surface
failed (careers, video, docs, press), and the archives section for history.

**Notes from past runs:** none yet.

## Investors (investors)

**Try first:** For a public company, SEC EDGAR filings, earnings call
transcripts, and investor day materials. For a private company, funding
releases, investor posts, founder interviews, and Form D filings. EDGAR
requires a descriptive `User-Agent` header with a contact address; use the
one given in `00-inputs/` or chat, and ask once if none is given.

- EDGAR full-text search: `https://efts.sec.gov/LATEST/search-index?q=<name>`
- Company filings: `https://data.sec.gov/submissions/CIK<10 digits>.json`

Check legal entities carefully. Treat analyst-only funding claims as
unconfirmed until matched by stronger evidence, and compare funding rounds
with the company's own "raised to date" boilerplate.

**Then try:**

1. The investor relations site's own press and events pages.
2. The investor's portfolio page and announcement post.
3. Wire copies of funding releases.
4. Crunchbase and PitchBook public pages as leads only, never as the
   receipt.

**Notes from past runs:** none yet.

## People and leadership (people)

**Try first:** The company's leadership, about, and team pages, with names,
titles, and dates. Cover leadership plus relevant product, engineering, AI,
marketing, sales, customer, and services leaders. Feed talks and podcast
appearances to the video and podcast channels.

**Then try:**

1. Speaker bios on event, webinar, and conference pages.
2. Bylines and author pages on the company blog.
3. Press releases that announce hires and promotions.
4. Podcast and talk introductions.
5. Wayback snapshots of the team page to date title changes.

**Notes from past runs:** none yet.

## Messaging history and archives (archives)

**Try first:** Wayback CDX for the homepage and top product pages, one
snapshot per quarter across the lookback:

```text
https://web.archive.org/cdx/search/cdx?url=<url>&output=json&from=<YYYY>&collapse=timestamp:6&filter=statuscode:200
```

Admit the raw snapshots as `https://web.archive.org/web/<timestamp>id_/<url>`.
The runtime dates each one from the archive timestamp. Record the title,
meta description, H1, and H2s per snapshot in the channel evidence.

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

**Try first:** The runtime extracts PDF text. By hand: `pdftotext -layout`
with page breaks marked.

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
