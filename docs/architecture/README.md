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

## Status

**Phase A (core design) — drafted, awaiting review.** Each document ends with *Open questions for
review*; those decisions gate Phase B.

## Phase B (after approval)

Sequence diagrams · project/folder scaffolding · complete `CLAUDE.md` · phased roadmap ·
GitHub Project (real Epics → Milestones → Issues via `gh`) · recommended implementation order.

## Conventions

- Each doc states **Status / Owner / Depends on** at the top.
- Design decisions record the **rejected alternative** and *why*, not just the choice.
- Drivers are referenced as **D1–D7** (defined in doc 01 §2).
