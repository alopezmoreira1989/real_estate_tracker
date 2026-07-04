# Architecture Decision Records

Every architecturally significant decision is recorded here as an immutable ADR: the context that
forced it, the decision itself, its consequences, and the alternatives rejected. New decisions get the
next number and a new file — **never edit an Accepted ADR's decision in place**; supersede it with a
new one and mark the old one's status `Superseded by ADR-NNN`. Use [template.md](template.md) as the
starting point.

## Register

| # | Title | Status |
|---|-------|--------|
| [001](001-clean-architecture.md) | Clean / hexagonal architecture with an inward-only dependency rule | Accepted |
| [002](002-domain-driven-design-lite.md) | Domain-Driven Design, deliberately "lite" | Accepted |
| [003](003-sqlalchemy-as-persistence.md) | SQLAlchemy for persistence; SQLite for MVP, PostgreSQL later | Accepted |
| [004](004-playwright-for-scraping.md) | Scraping: HTTP + BeautifulSoup by default, Playwright per portal when required | Accepted |
| [005](005-telegram-notifications.md) | Telegram as the first notification channel | Accepted |
| [006](006-import-linter.md) | Enforce the dependency rule mechanically with import-linter | Accepted |
| [007](007-poetry-dependency-management.md) | Dependency management: pip + setuptools, not Poetry | Accepted |
| [008](008-specification-pattern-rule-engine.md) | Rule Engine via the Specification pattern, Field Registry, and Operator Strategies | Accepted |
| [009](009-canonical-property-normalizer-confinement.md) | Canonical `Property` model; all portal knowledge confined to Normalizers | Accepted |
| [010](010-ine-coded-vocabularies.md) | Controlled vocabularies keyed by official INE codes | Accepted |
| [011](011-search-dedup-by-canonical-signature.md) | Search deduplication via a canonical query signature | Accepted |
| [012](012-notification-outbox.md) | Notifications via an outbox table, dispatched separately from scraping | Accepted |
| [013](013-defer-cross-portal-dedup.md) | Defer cross-portal deduplication for the MVP | Accepted |
| [014](014-condition-tree-and-only-mvp-ui.md) | Model the full condition tree; expose AND-only in the MVP UI | Accepted |
| [015](015-vocabulary-as-python-dicts.md) | Normalizer mapping/vocabulary tables as typed Python dicts | Accepted |
| [016](016-keyword-contains-python-then-db-fts.md) | Keyword CONTAINS filters run in the Python Rule Engine for the MVP | Accepted |
| [017](017-surrogate-uuid-primary-keys.md) | Surrogate UUID primary keys for domain aggregates | Proposed |

## Notes on revisiting

- **ADR-013** → revisit when duplicate cross-portal listings become a real UX annoyance; the backfill
  path is designed in [03-database.md](../03-database.md) §4.
- **ADR-016** → revisit if keyword filtering dominates evaluation cost at scale (doc 06 §2).
- **ADR-017** → benchmark index size on PostgreSQL before locking in for high-volume tables
  (`price_history`).

## History

This register was originally a single flat log (`docs/architecture/decisions.md`, ADR-001 through
ADR-013, all dated 2026-07-04 during initial design). It was split into individual files during
Phase 1.5 (repository hardening) so each decision could carry full context/consequences/alternatives,
and renumbered to interleave seven additional foundational decisions (001–007) that were implicit in
Phase 1's implementation but previously undocumented. Every prior ADR's content and intent is
preserved verbatim in its new file; only the id and filename changed. Every place that referenced an
old id (`CLAUDE.md`, `docs/roadmap.md`, `scripts/gh_setup.sh`) was updated to the new one in the same
change.
