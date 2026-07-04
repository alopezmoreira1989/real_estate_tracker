# 009 — Canonical `Property` model; all portal knowledge confined to Normalizers

> Status: **Accepted** · Date: 2026-07-04

## Context

Driver D2: portals disagree on field names, units, and vocabularies (`precio` vs `price`, `"120.000
€"` vs `120000`, "Suelo urbanizable" vs `URBANIZABLE`). If that variation leaks past the scraping
layer, the Rule Engine, database schema, notifications, and any future UI all have to know about every
portal's quirks — and every new portal ripples through the entire codebase.

## Decision

Define one canonical `Property` entity (doc 02 §2) that everything downstream of scraping speaks in.
The **only** component allowed to know a given portal's field names and spellings is that portal's
**Normalizer** (a domain port, implemented per portal in infrastructure — doc 05). Scrapers stay dumb:
they emit `RawListing`s (a faithful, uncleaned capture) and never interpret the data.

## Consequences

- Portal knowledge is confined to one seam (`infrastructure/normalizers/<portal>/`); the Rule Engine,
  persistence, and notifications are written once and never touched when a portal is added.
- Adding a portal is additive: a new scraper + normalizer + mapping tables + fixtures — OCP in
  practice (doc 07 "co-located per portal").
- The cost is translation work concentrated in normalizers, and the discipline of never adding a
  portal-specific `if portal == "idealista"` branch anywhere else in the codebase.

## Alternatives considered

- **Let each portal's raw shape flow through and branch downstream** — rejected: violates D2 directly,
  and every consumer (engine, DB, notifications) would need portal-awareness.
- **A generic key-value `Property` with no fixed shape** — rejected: loses type safety and the
  invariants VOs provide (doc 02 §2); the Rule Engine would need runtime type-checking everywhere.

## Revisit when

Not expected to change; this is the foundation the multi-portal roadmap (V2) depends on.
