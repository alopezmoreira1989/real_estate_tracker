# 01 — Architecture

> Status: **Draft for review** · Owner: Architecture · Supersedes: —

This document defines the high-level architecture of the **Real Estate Alert Platform**.
It is the reference every other design document (domain model, database, engines) must stay
consistent with.

---

## 1. Product in one paragraph

The platform continuously monitors multiple Spanish real-estate portals (Idealista, Fotocasa,
Pisos.com, Milanuncios, Habitaclia, …) and notifies users when **new listings match one or more
saved alerts**. An alert is a named, reusable search profile built from an arbitrary set of
**conditions**. The system scrapes each portal, **normalizes** heterogeneous listings into a single
**canonical `Property`**, evaluates every alert against new properties using a **rule engine**, and
dispatches **notifications** (Telegram first). It is single-user today and multi-tenant by design.

---

## 2. Architectural drivers (what shapes every decision)

| # | Driver | Consequence |
|---|--------|-------------|
| D1 | **New filters must be addable without touching the engine.** | Conditions are data, not columns. Rule Engine uses the Specification pattern. |
| D2 | **Portals differ in field names, units, and vocabularies.** | A per-portal Normalizer produces a canonical `Property`; nothing downstream knows about portals. |
| D3 | **Never scrape the same search N times for N alerts.** | Searches are deduplicated by a canonical query signature and cached (Search Engine). |
| D4 | **Notifications are orthogonal to scraping.** | Notification dispatch is decoupled via an outbox + channel adapters. |
| D5 | **Single user now, many users later.** | Every domain entity is owned by a `user_id`; no global singletons carrying user state. |
| D6 | **Portfolio-grade quality.** | Clean architecture, typed domain, tests, CI, documented decisions. |
| D7 | **Portals are hostile & change often.** | Scrapers are isolated, individually replaceable, and failure of one must not stop others. |

Non-goals for the MVP: horizontal scaling, real-time (<1 min) latency, ML-based deduplication of
physical properties, and a public multi-tenant sign-up flow.

---

## 3. Layered (Clean / Hexagonal) architecture

The system uses a **dependency rule**: source-code dependencies point **inwards only**. Inner layers
know nothing about outer layers.

```
┌───────────────────────────────────────────────────────────────────┐
│ Presentation        CLI · FastAPI (future) · Streamlit (future)     │
├───────────────────────────────────────────────────────────────────┤
│ Application         Use-cases / services · orchestration · DTOs     │
│                     (RunAlertCycle, CreateAlert, DispatchPending…)   │
├───────────────────────────────────────────────────────────────────┤
│ Domain              Entities · Value Objects · Rule/Alert Engine ·   │
│  (the core)         Ports (interfaces) · domain services · policies  │
├───────────────────────────────────────────────────────────────────┤
│ Infrastructure      Scrapers · Normalizers · SQLAlchemy repos ·      │
│  (adapters)         Telegram · Scheduler · HTTP clients · config     │
└───────────────────────────────────────────────────────────────────┘
        ▲ outer depends on inner            inner never imports outer ▲
```

### Layer responsibilities

- **Domain** — the heart. Pure Python, **zero third-party framework imports** (no SQLAlchemy, no
  Telegram, no Playwright, no FastAPI). Contains entities, value objects, the Rule/Alert Engine, and
  **Ports** (abstract interfaces such as `PropertyRepository`, `Scraper`, `Notifier`,
  `Normalizer`). Business invariants live here.
- **Application** — orchestrates use-cases by composing domain objects and calling ports. Owns
  transactions (Unit of Work), maps between DTOs and domain objects, and defines the *sequence* of a
  workflow (e.g. an alert cycle). Contains **no business rules** and **no I/O details**.
- **Infrastructure** — concrete implementations (**adapters**) of the domain ports: SQLAlchemy
  repositories, portal scrapers, per-portal normalizers, the Telegram notifier, APScheduler jobs,
  HTTP/Playwright clients, configuration loading.
- **Presentation** — entry points that trigger use-cases: a CLI (MVP), later a FastAPI API and a
  Streamlit dashboard. Thin; delegates immediately to the Application layer.

### The Dependency Rule, concretely

- Domain defines `class Scraper(Protocol)`. Infrastructure implements `IdealistaScraper(Scraper)`.
- Application depends on the **`Scraper` port**, never on `IdealistaScraper`.
- The **Composition Root** (in `infrastructure`/entry point) wires concrete adapters into use-cases
  via **Dependency Injection** (constructor injection). This is the *only* place that knows every
  concrete class.

> Rule of thumb: if you `import` something from an outer layer inside the domain, the design is
> broken. A lint boundary (import-linter) will enforce this in CI.

---

## 4. The core pipeline

```
Portal ──▶ Scraper ──▶ RawListing ──▶ Normalizer ──▶ Property ──▶ Alert/Rule Engine ──▶ AlertMatch ──▶ Notification
             (infra)    (DTO)          (infra)        (domain      (domain)               (domain)       (infra
                                                       entity)                                            adapter)
```

Each arrow is a boundary with a stable contract:

- `RawListing` — a faithful, portal-shaped capture (dict of raw fields + provenance). No cleaning.
- `Property` — the canonical, validated domain entity. The *only* thing the engine ever sees.
- `AlertMatch` — the fact that a given property satisfied a given alert at a given time (idempotent).
- `Notification` — a queued, channel-agnostic message; delivery is a separate concern.

See [02-domain-model.md](02-domain-model.md), [04-alert-rule-engine.md](04-alert-rule-engine.md),
and [05-normalization.md](05-normalization.md) for each stage.

---

## 5. Runtime view (an alert cycle)

The scheduler triggers the **`RunAlertCycle`** use-case per portal query group. High level:

1. **Plan** — collect due alerts, split their conditions into *portal-pushable* filters and
   *client-side* filters, compute a **canonical query signature** per portal, and deduplicate.
2. **Fetch** — for each unique signature, check `SearchCache`; on miss, run the portal `Scraper`,
   producing `RawListing`s, record a `SearchExecution`.
3. **Normalize** — the portal `Normalizer` converts each `RawListing` into a `Property`; upsert
   properties and append `PriceHistory` on change.
4. **Evaluate** — the Alert Engine evaluates each due alert's `Specification` against the candidate
   properties; new satisfactions become `AlertMatch` rows (deduplicated so a listing notifies once
   per alert).
5. **Notify** — new matches are written to the **notification outbox**; a separate dispatcher sends
   them via the user's channels honoring per-alert frequency.

Detailed sequence diagrams live in `docs/architecture/diagrams/` (Phase B).

---

## 6. Design patterns and where they apply

| Pattern | Where | Why |
|---------|-------|-----|
| **Specification** | Rule Engine (`AlertCondition` → composable `Specification`) | Add filters as data; combine with AND/OR/NOT without engine changes (D1). |
| **Strategy** | Comparison operators; per-portal scraping/parsing strategy | Swap behavior (operator, portal) behind one interface. |
| **Adapter** | Normalizers, Notifiers, Scrapers | Translate an external shape/protocol into a domain port. |
| **Factory** | Build `Specification` from persisted conditions; select Scraper/Normalizer/Notifier by portal/channel | Centralize construction + registration. |
| **Repository** | Persistence of every aggregate | Domain speaks in collections, not SQL. |
| **Unit of Work** | Application transactions | One consistent commit boundary per use-case. |
| **Registry** | Field resolvers, portal & channel registries | Pluggable, discoverable extension points. |
| **Dependency Injection** | Composition root | Invert control; testability; honor the dependency rule. |
| **Outbox** | Notification queue | Decouple match detection from delivery; retryable, orthogonal (D4). |

Patterns are applied **only where they earn their keep** — see each engine doc for the rationale and
the "simpler alternative rejected because…" note.

---

## 7. Technology mapping (per layer)

| Layer | Tech |
|-------|------|
| Domain | Pure Python 3.12, `dataclasses`/`enum` (no framework deps) |
| Application | Python, Pydantic (DTOs/validation at boundaries) |
| Infrastructure | SQLAlchemy 2.x + Alembic, APScheduler, httpx, BeautifulSoup, Playwright (only if a portal requires JS) |
| Persistence | SQLite (MVP) → PostgreSQL (later); same code via SQLAlchemy |
| Presentation | Typer CLI (MVP) → FastAPI + Streamlit (later) |
| Cross-cutting | `structlog` logging, `pydantic-settings` config, `tenacity` retries, `cryptography` (Fernet) for channel-secret encryption at rest |

> **Phase 6 supersession:** `TelegramNotifier` sends via a plain `httpx` POST to the Bot API
> (`sendMessage`), not `python-telegram-bot` — that library is async-first, while the rest of the
> scraping/notification infrastructure (e.g. `IdealistaScraper`) is synchronous `httpx`. The
> Telegram *channel* choice itself is unchanged (ADR-005); this only settles the client library.
| Quality | pytest, ruff, black, mypy, import-linter, pre-commit, GitHub Actions, Docker |

---

## 8. Cross-cutting concerns (summary; full policy in CLAUDE.md, Phase B)

- **Configuration** — 12-factor; typed settings via `pydantic-settings`; secrets from env, never
  committed.
- **Logging** — structured (`structlog`), correlation id per alert cycle, no PII/secrets in logs.
- **Error handling** — domain raises typed domain errors; infrastructure wraps external failures;
  one scraper failing is isolated and logged, the cycle continues.
- **Resilience** — per-portal rate limiting, backoff/retry (`tenacity`), politeness (robots, delays),
  circuit-breaking a failing portal.
- **Security** — respect portal ToS/robots where legally required, store credentials/tokens
  encrypted, principle of least privilege, input validation at boundaries.
- **Idempotency** — `AlertMatch` and outbox entries are idempotent so re-runs never double-notify.

---

## 9. Multi-tenancy from day one

- Every user-owned entity (`SearchAlert`, `AlertCondition`, `Notification`, notification channels)
  carries `user_id`.
- Shared, non-user data (`Portal`, `Property`, `PriceHistory`, `SearchCache`) is **global** and
  reused across users — this is *why* the Search Engine dedup (D3) also saves work across tenants.
- No module holds "the current user" as global state; the user is an explicit parameter/context of a
  use-case.

---

## 10. Open questions for review

1. **Physical-property dedup**: do we treat the same flat listed on 3 portals as 3 `Property` rows
   linked by a fingerprint, or 1 canonical `Property` with N `PortalListing`s? (Proposed:
   `PortalListing` = scraped record, `Property` = canonical/deduped — see
   [03-database.md](03-database.md) §Dedup. Confirm we want this complexity in the MVP or defer.)
2. **Playwright vs HTTP**: adopt Playwright only per-portal on demand, or standardize now?
   (Proposed: HTTP+BeautifulSoup default, Playwright per-portal opt-in.)
3. **Alert condition logic**: AND-only across conditions for MVP, or full boolean groups (AND/OR/NOT
   trees) from the start? (Proposed: model the tree in the domain, expose AND-only in the MVP UI.)

These are resolved in the linked engine docs with a recommendation; flag any you disagree with.
