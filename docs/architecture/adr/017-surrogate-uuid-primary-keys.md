# 017 — Surrogate UUID primary keys for domain aggregates

> Status: **Proposed** · Date: 2026-07-04

## Context

Domain aggregates (`Property`, `SearchAlert`, `AlertMatch`, `User`, …) need a primary key strategy.
Auto-incrementing integers are compact and index-friendly but reveal row counts/creation order and
complicate merging data across environments or future sharding; UUIDs are opaque and
merge-friendly but larger, with index-locality trade-offs that matter more at high write volume.

## Decision (proposed)

Use **surrogate UUID primary keys** for domain aggregates, wrapped in typed id classes (`PropertyId`,
`AlertId`, …) per CLAUDE.md §4 so raw strings/ints never cross a boundary as an identifier. High-volume,
append-only tables where index size dominates (`price_history`) may use a `bigint` surrogate key
instead — this specific case is **not yet locked in**, pending a benchmark (see *Revisit when*).

## Consequences

- Ids are multi-tenant-opaque (no information leaks by comparing two ids) and merge-friendly (no
  collision risk when combining data from different environments/backfills).
- Every id is a distinct Python type (`PropertyId` vs `AlertId`), so passing the wrong id to the wrong
  repository method is a type error, not a runtime bug (CLAUDE.md §4).
- UUID primary keys are larger than integers and can fragment B-tree indexes under high insert volume
  — a real cost for `price_history`, which is exactly why that table's key type is still open.

## Alternatives considered

- **Auto-increment integers everywhere** — simpler, smaller, better index locality; rejected as the
  default because it leaks ordering/volume information and complicates cross-environment merges, which
  matter once V2 (multi-portal) and V3 (multi-user) scale up data volume and operational complexity.
- **ULID/KSUID** (sortable, UUID-like ids) — would give UUID's opacity plus better index locality than
  random UUIDv4. Not chosen yet, but a candidate if the `price_history` benchmark (below) shows UUIDv4
  index fragmentation is a real problem — worth trying before falling back to `bigint`.

## Revisit when

Before locking this in for high-volume tables (`price_history` specifically), benchmark index size and
write throughput on PostgreSQL with realistic data volumes; this ADR stays **Proposed** until that
benchmark is done.
