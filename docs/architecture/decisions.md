# Architecture Decision Register

Lightweight ADR log. Each entry: the decision, the context, and the rejected alternative. Referenced
by the design docs and by `CLAUDE.md`.

| ID | Decision | Status | Date |
|----|----------|--------|------|
| ADR-001 | Clean/hexagonal layering with an inward-only dependency rule; domain is framework-free | Accepted | 2026-07-04 |
| ADR-002 | Rule Engine uses the Specification pattern + Field Registry + Operator Strategies (conditions are data, not columns) | Accepted | 2026-07-04 |
| ADR-003 | Canonical `Property` domain model; all portal knowledge confined to per-portal Normalizers | Accepted | 2026-07-04 |
| ADR-004 | Controlled vocabularies keyed by official **INE codes** for province/municipality | Accepted | 2026-07-04 |
| ADR-005 | Search dedup via a **canonical query signature**; one scrape per signature, fanned out across alerts and users | Accepted | 2026-07-04 |
| ADR-006 | Notifications via an **outbox** table, dispatched by a separate job; delivery decoupled from scraping | Accepted | 2026-07-04 |
| ADR-007 | SQLite for MVP, PostgreSQL later; single SQLAlchemy model set + Alembic migrations from day one | Accepted | 2026-07-04 |
| ADR-008 | **Defer cross-portal dedup** (1:1 `PortalListing`↔`Property`) for MVP; schema supports later merge via nullable `fingerprint` + backfill | Accepted | 2026-07-04 |
| ADR-009 | Condition **tree** (AND/OR/NOT) modeled in domain + DB; MVP UI exposes **AND-only** (single top-level `ALL` group) | Accepted | 2026-07-04 |
| ADR-010 | Scraping defaults to **httpx + BeautifulSoup**; Playwright adopted **per-portal** only when JS rendering is required | Accepted | 2026-07-04 |
| ADR-011 | Normalizer mapping/vocabulary tables as **typed Python dicts** (not YAML) while a developer owns them | Accepted | 2026-07-04 |
| ADR-012 | Keyword `CONTAINS` filters evaluated in the **Python Rule Engine** for MVP (identical across DBs); push to DB FTS later as an optimization | Accepted | 2026-07-04 |
| ADR-013 | Surrogate **UUID** primary keys for domain aggregates (merge-friendly, multi-tenant opaque); `bigint` where volume dominates (`price_history`) may be revisited | Proposed | 2026-07-04 |

## Notes on revisiting

- ADR-008 → revisit when duplicate listings become a real UX annoyance; the backfill path is
  designed in [03-database.md](03-database.md) §4.
- ADR-012 → revisit if keyword filtering dominates evaluation cost at scale (doc 06 §2).
- ADR-013 → benchmark index size on PostgreSQL before locking in for high-volume tables.

New decisions append here with the next ADR id and are cross-linked from the affected design doc.
