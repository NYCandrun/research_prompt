# TASK TYPE: COMPETITOR SOURCE DISCOVERY

Discover public evidence for the one competitor named in this packet's inputs.
Record every pass with `discovery add --channel competitor:SLUG`, using the
exact channel in the packet. Sources you add are tagged with this competitor
as their subject, and facts extracted from them are filed under
`04-competitors/SLUG/`.

Cover, more lightly than the company itself:

- the competitor's website and key product pages;
- pricing and packaging;
- docs, help center, or knowledge base, only for the product that competes
  with the company's products in focus. For a suite, stay within that
  product. Cap docs at about 400 pages and name what was left out in the
  channel evidence;
- press releases over the lookback;
- two or three leader talks when useful;
- review sites and marketplace listings;
- two homepage snapshots from the archives, one recent and one at the start of
  the lookback;
- the competitor's own pages that describe the company being researched.

Competitor videos are out of scope except ones the company embeds on its own
pages. Do not transcribe videos found inside competitor docs.

The channel reaches a fixed point when materially different passes add no new
relevant sources within those boundaries. Then run
`discovery receipt --channel competitor:SLUG`. If the competitor's surfaces are
blocked, work through the playbook sections in this packet first, then close
the channel as `blocked` with every approach tried.
