# Architecture Documentation

Foundational design for the **Real Estate Alert Platform**. Read in order — each builds on the
previous. Diagrams are Mermaid (rendered natively by GitHub).

| # | Document | Covers |
|---|----------|--------|
| 01 | [Architecture](01-architecture.md) | Drivers, clean/hexagonal layers, dependency rule, pipeline, patterns, tech mapping, multi-tenancy |
| 02 | [Domain Model](02-domain-model.md) | Canonical `Property`, value objects, controlled vocabularies, the Alert aggregate |
| 03 | [Database](03-database.md) | ERD, tables, keys, indexes, constraints, dedup, SQLite→PostgreSQL |
| 04 | [Alert & Rule Engine](04-alert-rule-engine.md) | Specification pattern, field registry, operator strategies, factory, orchestration |
| 05 | [Normalization](05-normalization.md) | `RawListing`→`Property`, mapping/vocab tables, registry, observability |
| 06 | [Search & Scheduler](06-search-scheduler.md) | Query dedup by signature, caching, APScheduler strategy, resilience |
| 07 | [Folder Structure](07-folder-structure.md) | Physical layout, one-to-one mapping onto the layers, per-folder responsibilities |
| 08 | [Sequence Diagrams](08-sequence-diagrams.md) | Runtime flows: create alert, alert cycle, notification dispatch, scraper failure isolation |
| 09 | [System Diagrams](09-diagrams.md) | System context, layered architecture, dependency flow, package relationships, future deployment |
| 10 | [Future-Proofing & Risks](10-future-proofing.md) | Extension points and risks for new portals, channels, API, UI, auth, deployment, multi-user |

Architecture **decisions** live in [adr/](adr/) — one immutable file per decision, indexed in
[adr/README.md](adr/README.md).

## Status

Docs 01–08 are the **accepted** Phase A/B design; the platform is being implemented against them
(see [../roadmap.md](../roadmap.md) for current phase). Docs 09–10 were added during **Phase 1.5**
(repository hardening) to make the already-implicit architecture and its risks explicit before domain
work (Phase 2) begins.

## Conventions

- Each doc states **Status / Owner / Depends on** at the top.
- Design decisions record the **rejected alternative** and *why* — either inline, or as a linked ADR
  in [adr/](adr/) for decisions significant enough to need their own Context/Consequences record.
- Drivers are referenced as **D1–D7** (defined in doc 01 §2).
- Terminology is fixed project-wide: **`Listing`** is what a portal shows before normalization
  (captured as `RawListing`, persisted as `PortalListing`); **`Property`** is always the canonical,
  normalized entity; **`SearchAlert`** (or **`Alert`** for short) is the user's saved search profile;
  **`Rule`**/**Rule Engine** refers to the Specification-based predicate evaluator, never to a
  database trigger or a notification rule. See [CLAUDE.md](../../CLAUDE.md) §1 for the canonical
  glossary.
