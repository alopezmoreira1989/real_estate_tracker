# 004 — Scraping: HTTP + BeautifulSoup by default, Playwright per portal when required

> Status: **Accepted** · Date: 2026-07-04

## Context

Spanish real-estate portals (Idealista, Fotocasa, Pisos.com, Milanuncios, Habitaclia) render listing
pages differently: some serve fully-formed server-rendered HTML, others hydrate content client-side
via JavaScript. A browser-automation tool (Playwright) can scrape either kind, but it is an order of
magnitude heavier — a real browser process per fetch, slower page loads, more memory, and a much
larger dependency footprint — than an HTTP client parsing static HTML. Driver D7 ("portals are
hostile and change often") means every scraper needs to be individually replaceable and its resource
cost predictable, since the platform will eventually run several scrapers concurrently under a
per-portal rate limiter (see [06-search-scheduler.md](../06-search-scheduler.md) §5).

## Decision

Every portal scraper defaults to **`httpx` + `BeautifulSoup`** against the portal's static HTML.
**Playwright is adopted per portal, only when that specific portal requires JavaScript rendering to
expose listing data** — it is an opt-in escape hatch selected in that portal's scraper package, not a
platform-wide dependency. The first scraper (Idealista, [roadmap.md](../../roadmap.md) Phase 5) ships
with BeautifulSoup; Playwright is added only if Idealista (or a later portal) is confirmed to require
it.

## Consequences

- Most scrapers stay lightweight (no browser binary, fast fetch, low memory) — this keeps per-portal
  concurrency (D7) cheap to scale.
- The scraper `Protocol`/port (ADR-001) does not leak *how* a page was fetched — Application and
  Domain never know whether a given portal used `httpx` or Playwright, so mixing strategies across
  portals is transparent to the rest of the system.
- The cost is a second code path to maintain once any portal needs Playwright: browser install/update
  in CI and Docker images, longer scrape latency for that portal specifically, and a different
  failure mode (browser crashes/timeouts) that the circuit breaker (ADR-001, doc 06 §5) must also
  cover.
- Portal-by-portal opt-in means the decision of "does this portal need a browser" is made once, with
  evidence (the static fetch actually failing to expose data), rather than speculatively for every
  portal.

## Alternatives considered

- **Playwright for every portal (standardize now)** — one code path for all portals, simpler mental
  model, but pays browser-automation overhead even for portals that never needed it. Rejected: this
  was one of the two options raised as an open question in
  [01-architecture.md](../01-architecture.md) §10 and resolved in favor of the lighter default.
- **`httpx`/`requests` only, no Playwright ever** — simplest, but silently fails (or requires ad-hoc
  hacks) the moment one portal turns out to require JS rendering, blocking that portal entirely.
  Rejected as too rigid given D7.
- **A headless-browser-as-a-service (e.g. a remote rendering API)** — removes the local Playwright
  dependency but adds an external service dependency, cost, and another failure mode outside our
  control. Not worth it while a locally-run Playwright instance suffices; revisit only at a scale
  where running browsers locally becomes the bottleneck.

## Revisit when

A specific portal is confirmed (via a failing BeautifulSoup contract test) to require JS rendering —
at that point Playwright is added for *that portal's* scraper package only, per this ADR, not as a
platform-wide change.
