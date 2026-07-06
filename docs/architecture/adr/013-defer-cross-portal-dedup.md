# 013 — Defer cross-portal deduplication for the MVP

> Status: **Accepted** · Date: 2026-07-04

## Context

The same physical flat is often listed on more than one portal (Idealista *and* Fotocasa). Merging
those into a single canonical `Property` (rather than one per portal listing) requires a `fingerprint`
computed from fuzzy signals (address/geo, area, rooms, property type) — a nontrivial matching problem
with false-positive/false-negative trade-offs. Building it before the rest of the pipeline exists would
be speculative.

## Decision

Ship the MVP with **1:1 `PortalListing`↔`Property`** — no cross-portal merge, `fingerprint` present in
the schema but nullable and unused. The schema already supports the later merge
(`PortalListing.property_id` FK, nullable `fingerprint` — doc 03 §4) so enabling it later is a backfill
migration, not a schema redesign.

## Consequences

- The MVP is simpler and ships faster; the user sees the same physical property twice if it's
  cross-listed — a known, accepted UX rough edge for V1.
- No fuzzy-matching logic (and its false-positive risk of wrongly merging two different properties) is
  needed until it's actually built and tuned deliberately.
- The eventual merge is additive: compute `fingerprint` for existing rows, backfill, then start
  deduping new listings — no data model change at that point (doc 03 §4 already designs the backfill
  path).

## Alternatives considered

- **Build fingerprint-based merge now** — rejected: speculative before the single-portal pipeline even
  exists (Phase 5 is Idealista-only); premature complexity (YAGNI).
- **Never support cross-portal dedup** — rejected: multi-portal duplicate listings are a real,
  expected annoyance once Fotocasa/Pisos.com are added (V2); the schema cost of keeping the door open
  (`fingerprint` nullable column) is negligible.

## Revisit when

Duplicate listings across portals become a real UX annoyance (i.e. once a second portal is live and
users notice duplicates) — the backfill path is already designed in
[03-database.md](../03-database.md) §4.
