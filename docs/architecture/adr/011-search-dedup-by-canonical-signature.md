# 011 — Search deduplication via a canonical query signature

> Status: **Accepted** · Date: 2026-07-04

## Context

Driver D3: if ten alerts (from one user or many) all watch "land in Pontevedra," the platform must not
scrape Pontevedra ten times. Naively running each alert's search independently multiplies scraping
cost linearly with alert count instead of with distinct searches.

## Decision

Split every alert's conditions into **portal-pushable** (server-side filterable) and **client-side**
(evaluated by the Rule Engine) buckets, reduce the pushable subset to a **canonical query signature**
(portal + normalized, sorted, hashed parameters), and cache/execute **one scrape per unique signature
per cycle**, fanned out to every alert that shares it — regardless of which user owns the alert. Full
design: [06-search-scheduler.md](../06-search-scheduler.md).

## Consequences

- Scraping cost scales with **distinct searches**, not with alert or user count (CLAUDE.md §13) — the
  concrete payoff of D3 and, as a side effect, the multi-tenant cost model (doc 01 §9).
- The pushable subset is intentionally coarse (shared widely); precision is recovered client-side by
  the Rule Engine, so two alerts sharing a scrape can still have different final match sets.
- Requires portal `capabilities` config (which fields are server-side filterable) to be accurate — a
  wrong capability either over-pushes (portal rejects the query) or under-pushes (unnecessary
  client-side filtering of a huge result set).

## Alternatives considered

- **One scrape per alert** — rejected: violates D3 directly, cost scales with alert count.
- **Widening/superset dedup** (fetch a superset once, filter multiple alerts from it) — a genuine
  future optimization (doc 06 §2), deferred: MVP's exact-signature dedup already eliminates the
  "10× Pontevedra" case with far less complexity.

## Revisit when

Query-widening (doc 06 §2) becomes worth it once near-duplicate (not identical) signatures are common
enough to matter — tracked as a V2 backlog item.
