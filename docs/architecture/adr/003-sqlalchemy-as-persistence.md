# 003 — SQLAlchemy for persistence; SQLite for MVP, PostgreSQL later

> Status: **Accepted** · Date: 2026-07-04

## Context

The platform needs relational persistence for `Property`, `SearchAlert`, `AlertMatch`, the
notification outbox, and search-execution/cache bookkeeping (full schema:
[03-database.md](../03-database.md)). A single engineer is running this for personal use today
(driver: single-user MVP), but the roadmap explicitly plans a PostgreSQL migration in V2 once
concurrency, JSONB attribute indexing, and full-text search matter (roadmap.md, V2). Rewriting the
persistence layer at that point would be expensive if today's code assumes a specific engine.

## Decision

Use **SQLAlchemy 2.x** (ORM + Core) as the single mapping layer for both engines, with **Alembic**
migrations from day one, so the MVP runs on **SQLite** and V2 moves to **PostgreSQL** by changing a
connection string and a small number of dialect-specific column types (`JSON`→`JSONB` with GIN
indexes, `CHAR(36)`→native `uuid`) — never the table shapes or the repository code that domain/
application see. Repositories implement the domain's `*Repository` ports (ADR-001); nothing outside
`infrastructure/persistence` imports SQLAlchemy.

## Consequences

- One model set, one migration history, one repository implementation to test — no parallel
  "SQLite path" and "Postgres path" to keep in sync.
- SQLite's limitations are accepted for the MVP: single-writer concurrency, weaker JSON querying, no
  native full-text search beyond FTS5. These match the MVP's actual load (one user, a scheduler
  running every ~60s) — see [ADR-016](016-keyword-contains-python-then-db-fts.md) for how keyword
  filtering avoids depending on FTS in the meantime.
- The migration to PostgreSQL is a planned, scoped piece of work (V2), not a rewrite — attribute
  filters move from Python-side JSON inspection to indexed `JSONB`/GIN only when the doc says so.
- Alembic migrations are mandatory even in the SQLite phase, so the migration history itself (not just
  the final schema) carries forward into V2 rather than being reconstructed from scratch.

## Alternatives considered

- **Raw SQL / a micro query builder** — less abstraction overhead, but hand-maintaining two dialects'
  worth of SQL (SQLite now, Postgres later) duplicates the whole persistence layer at migration time.
  Rejected.
- **An async ORM (e.g. SQLAlchemy 2.x async, Tortoise)** — the MVP's scheduler-driven, batch-style
  workload (one alert cycle every ~60s, not per-request concurrency) does not need async I/O; sync
  SQLAlchemy is simpler to reason about and test. Rejected for now; revisit if a high-concurrency
  FastAPI surface (V2) makes request-path blocking I/O a real bottleneck.
- **Document store (e.g. SQLite-as-JSON-blob-store, or MongoDB)** — `Property` has genuinely
  relational structure (price history, alert matches, portal listings) that benefits from joins and
  foreign-key integrity; a document model would push that relational work back into application code.
  Rejected.

## Revisit when

The PostgreSQL migration is triggered by the V2 entry criteria already stated in
[docs/roadmap.md](../../roadmap.md): concurrent writers, `JSONB`/GIN attribute filtering, or
full-text search becoming necessary.
