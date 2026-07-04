# 001 — Clean / hexagonal architecture with an inward-only dependency rule

> Status: **Accepted** · Date: 2026-07-04

## Context

The platform's core value — matching new listings against arbitrary, evolving alert conditions — has
to survive churn in everything around it: portals change their HTML, the persistence engine moves
from SQLite to PostgreSQL (V2), notification channels multiply, and a CLI gets joined by a REST API
and a web dashboard. If business rules are entangled with SQLAlchemy models, HTTP handlers, or
scraping code, every one of those changes risks breaking rule evaluation. The team is also a single
engineer today and several later — the design has to be legible to someone who wasn't there when a
decision was made.

## Decision

Structure the codebase as four layers — **Domain → Application → Infrastructure /
Presentation** — with a single rule: **source-code dependencies point inward only.** The domain layer
imports nothing but the Python standard library. Outer layers depend on domain-defined **ports**
(abstract interfaces: `Scraper`, `Normalizer`, `Notifier`, `*Repository`, `UnitOfWork`); concrete
implementations (**adapters**) live in infrastructure and are wired together in a single
**composition root** (`composition.py`) via constructor-based dependency injection. See
[01-architecture.md](../01-architecture.md) §3 for the full layer diagram and
[07-folder-structure.md](../07-folder-structure.md) for the physical mapping.

The rule is enforced mechanically, not by convention — see [ADR-006](006-import-linter.md).

## Consequences

- The domain (entities, value objects, the Rule Engine) is testable with zero mocks and zero I/O —
  fast, deterministic unit tests are the default, not the exception.
- Swapping SQLite for PostgreSQL, or adding a second scraper, touches infrastructure only; the Rule
  Engine and use-cases are unaware either happened.
- The cost is upfront ceremony: every new capability needs a port defined before it can be
  implemented, and a small amount of interface/adapter boilerplate that a single-file script wouldn't
  need. For a project meant to run unattended for years and to add portals/channels/users
  incrementally, that ceremony is judged worth it (driver D6, portfolio-grade quality).
- New contributors must internalize "who may import whom" before their first PR; this is why the rule
  is documented in [CLAUDE.md](../../../CLAUDE.md) §2 and re-stated in the diagrams doc, not left
  implicit.

## Alternatives considered

- **Transaction-script / "fat" use-case functions calling the ORM directly** — fastest to write
  initially, but business rules (what counts as a match, how conditions combine) end up scattered
  across use-cases and duplicated wherever they're needed again (e.g. a future API). Rejected: it
  directly undermines D1 (new filters must be addable without touching evaluation code).
- **Django-style "fat models"** (business logic on ORM-mapped classes) — couples the domain to the
  persistence framework from day one, making the SQLite→PostgreSQL move (and the domain-purity tests
  in CLAUDE.md §8) impossible without a rewrite. Rejected.
- **Full onion/hexagonal with a separate package per layer** (e.g. `real_estate_domain`,
  `real_estate_infra` as independently installable distributions) — enforces the boundary even harder,
  but the packaging/versioning overhead is unjustified for a single-deployable application. Rejected
  as premature; the current single-package, import-linter-enforced boundary gets the same guarantee
  at a fraction of the operational cost.

## Revisit when

If the project ever splits into independently deployable services (e.g. a scraping worker fleet
separate from the API), promoting `domain`/`application` to their own installable package becomes
worth re-evaluating.
