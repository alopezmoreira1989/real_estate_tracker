# 016 — Keyword CONTAINS filters run in the Python Rule Engine for the MVP

> Status: **Accepted** · Date: 2026-07-04

## Context

Alerts can filter on free-text keywords in a description (`CONTAINS "water"`, `NOT_CONTAINS
"occupied"`), including accent/case-insensitive matching (`agua` vs `água`). This could be evaluated
in the database (SQL `LIKE`, or full-text search) or in the Python Rule Engine after fetching
candidate properties.

## Decision

Evaluate `CONTAINS`/`NOT_CONTAINS` in the **Python Rule Engine** for the MVP, identically regardless of
whether the underlying database is SQLite or (later) PostgreSQL — see
[ADR-003](003-sqlalchemy-as-persistence.md). The Search Engine (ADR-011) already narrows candidates to
a small, relevant set via portal-pushable filters before the Rule Engine runs, so the Python-side
keyword pass operates on a small result set, not the whole table.

## Consequences

- Identical keyword-matching behavior across SQLite (MVP) and PostgreSQL (V2) — no dialect-specific SQL
  to keep in sync, and no FTS index to maintain yet.
- Accent-folding and case-insensitivity are implemented once, in one operator strategy (doc 04 §4),
  rather than as database-specific `COLLATE`/extension configuration.
- The cost is evaluating keyword matches in Python rather than pushing them to the database — accepted
  because the Search Engine's pre-filter (ADR-011) keeps candidate-set sizes small at MVP scale.

## Alternatives considered

- **Push to DB FTS (SQLite FTS5 / PostgreSQL `tsvector`+`pg_trgm`) now** — better scaling for large
  candidate sets and large keyword vocabularies, but adds dialect-specific index/query code before
  there's evidence it's needed, and would need two implementations to stay consistent across SQLite
  and PostgreSQL during the exact period the project is migrating between them. Deferred as an
  optimization, not rejected outright.

## Revisit when

Keyword filtering is measured to dominate evaluation cost at scale (doc 06 §2) — push to DB
full-text search as an optimization at that point, without changing the domain-level `CONTAINS`
contract.
