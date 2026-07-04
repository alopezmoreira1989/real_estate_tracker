# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository. **Read this before writing code.**
It defines how the Real Estate Alert Platform is built and how it must evolve. When in doubt, follow
this file and the design docs in [docs/architecture/](docs/architecture/); if you must deviate,
record an ADR in [docs/architecture/decisions.md](docs/architecture/decisions.md).

---

## 1. Project overview

The platform monitors Spanish real-estate portals (Idealista, Fotocasa, Pisos.com, Milanuncios,
Habitaclia, …) and notifies users when **new listings match saved alerts**. An **alert** is a named,
reusable search profile made of arbitrary **conditions**. Listings are scraped, **normalized** into a
canonical `Property`, evaluated by a **Rule Engine**, and matches are dispatched via **notifications**
(Telegram first). Single-user today, **multi-tenant by design**.

Full design: start at [docs/architecture/README.md](docs/architecture/README.md).

---

## 2. Architecture principles

- **Clean / hexagonal architecture** with four layers: Presentation → Application → Domain ←
  Infrastructure. See [01-architecture.md](docs/architecture/01-architecture.md).
- **The Dependency Rule (non-negotiable):** source dependencies point **inward only**. The `domain`
  layer imports **nothing** but the standard library — no SQLAlchemy, Pydantic, Telegram, Playwright,
  or FastAPI. Enforced in CI by **import-linter**.
- **Ports & Adapters:** the domain defines abstract **ports** (`Scraper`, `Normalizer`, `Notifier`,
  `*Repository`, `UnitOfWork`); infrastructure provides **adapters**. Only `composition.py` knows
  concrete classes (Dependency Injection).
- **Conditions are data, not columns** (driver D1): the Rule Engine uses the **Specification**
  pattern + a **Field Registry**; adding a filter = registering a `FieldDescriptor`, never editing
  the engine. See [04-alert-rule-engine.md](docs/architecture/04-alert-rule-engine.md).
- **All portal knowledge is confined to Normalizers** (driver D2): downstream code never knows a
  portal exists. See [05-normalization.md](docs/architecture/05-normalization.md).
- **Deduplicate searches** (driver D3): one scrape per canonical query signature, reused across
  alerts and users. See [06-search-scheduler.md](docs/architecture/06-search-scheduler.md).
- **Notifications are decoupled** via an outbox (driver D4).
- **Multi-tenant from day one** (driver D5): every user entity carries `user_id`; no global user
  state.

Drivers D1–D7 are defined in [01-architecture.md §2](docs/architecture/01-architecture.md).

---

## 3. Folder conventions

`src`-layout package `src/real_estate/` mirrors the layers exactly; `tests/` mirrors `src/`
path-for-path. Portal code (scraper + normalizer + mapping tables) is **co-located per portal**.
Full map + per-folder responsibility table:
[07-folder-structure.md](docs/architecture/07-folder-structure.md).

**Where does new code go?**
- A business rule / invariant / the "does it match" question → `domain/`.
- Orchestrating a workflow across ports → `application/use_cases/`.
- Talking to a DB, website, or external API → `infrastructure/`.
- A new entry point (command, endpoint, page) → `presentation/`.
- If you're unsure whether something is domain or infrastructure: does it import a third-party I/O
  library? Then it's infrastructure.

---

## 4. Coding standards

- **Python 3.12+**, full **type hints** everywhere; `mypy` runs in **strict** mode and must pass.
- **Ruff** (lint + isort) and **Black** (format) are authoritative; do not hand-format around them.
- Prefer **`@dataclass(frozen=True)`** for value objects; immutable by default.
- Pydantic is for **boundaries only** (DTOs, config, API schemas) — never leak Pydantic models into
  the domain.
- No bare `except:`; catch specific exceptions. No mutable default arguments. No `print` — use the
  logger.
- Public functions/classes have docstrings stating intent, not restating code. Comments explain
  **why**, not what.
- Keep functions small and single-purpose (SRP). If a function needs a comment to separate "steps",
  those steps are probably functions.

### Naming conventions

- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE` constants,
  `_leading_underscore` for non-public.
- Ports are nouns (`PropertyRepository`); adapters name their tech (`SqlAlchemyPropertyRepository`,
  `IdealistaScraper`, `TelegramNotifier`).
- Use-cases are imperative verbs (`RunAlertCycle`, `CreateAlert`).
- Typed id wrappers: `PropertyId`, `AlertId`, … (never pass raw `str`/`int` ids across boundaries).
- Test files: `test_<module>.py`; test functions: `test_<behavior>_<condition>_<expected>()`.

---

## 5. Python best practices & design principles

- **SOLID**
  - *SRP* — one reason to change per module/class (a scraper scrapes; a normalizer normalizes).
  - *OCP* — extend by adding (a new `FieldDescriptor`, a new portal package), not by editing engines.
  - *LSP* — every `Scraper`/`Normalizer`/`Notifier` is substitutable behind its port.
  - *ISP* — small, focused ports; don't force adapters to implement unused methods.
  - *DIP* — depend on domain ports, not concrete infrastructure; wire in the composition root.
- **DRY** — shared parsing/formatting lives once (e.g. Spanish locale number parsers in
  normalization); duplicate *knowledge* is the enemy, not duplicate lines.
- **KISS** — the simplest design that satisfies the drivers. Patterns are applied only where they
  earn maintainability (each engine doc records the *rejected simpler alternative* and why).
- **YAGNI** — build for the current phase (see roadmap); the architecture leaves seams for the
  future without pre-building it (e.g. condition tree modeled now, AND-only UI shipped — ADR-009).

---

## 6. Dependency rules (enforced)

`import-linter` contracts in `pyproject.toml`:
- `domain` may import only the standard library.
- `application` may import `domain` only.
- `infrastructure` may import `domain` (+ `application` where it implements a use-case port).
- `presentation` may import `application` (+ `domain` types).
- Nothing may import `presentation` or `infrastructure` except `composition.py`/entry points.

A PR that breaks a contract fails CI. Fix the design, don't relax the contract (relaxing requires an
ADR + reviewer sign-off).

---

## 7. Design patterns used (and why)

| Pattern | Where | Doc |
|---------|-------|-----|
| Specification (+ composites) | Rule Engine | 04 |
| Strategy | operators, per-portal scraping | 04, 05 |
| Adapter | normalizers, notifiers, scrapers | 05, 08 |
| Factory + Registry | spec building; portal/normalizer/channel selection | 04, 05 |
| Repository | persistence of aggregates | 03 |
| Unit of Work | transaction boundary per use-case | 03 |
| Dependency Injection | composition root | 01 |
| Outbox | notification queue | 03, 08 |

Do not introduce a new pattern without stating the problem it solves in the PR/ADR.

---

## 8. Testing philosophy

- **The testing pyramid:** many fast **unit** tests (domain + application, zero I/O), fewer
  **integration** tests (repositories, scrapers vs *recorded fixtures*, DB), a few **e2e** tests
  (full alert cycle on a seeded DB).
- **Domain is tested without mocks** — it's pure. Mock only at **ports**.
- Scrapers/normalizers are tested against **recorded `RawListing` fixtures** (`tests/fixtures/`), so
  portal changes surface as failing golden tests, not silent data drift.
- The Rule Engine has the **"Urbanizable land in Pontevedra"** golden fixture + property-based
  (Hypothesis) tests for algebraic laws.
- **Coverage** is a signal, not a target; a bug fix ships with a test that fails without the fix.
- Tests must be deterministic (inject a `Clock`/`IdGenerator`; no real network, no `datetime.now()`
  in logic).

---

## 9. Git workflow, branches & commits

### Branch strategy
- **`main`** — always releasable; protected. Only receives reviewed, verified merges.
- **`dev_alm`** — the integration branch for ongoing development. **Do work here** (or in
  short-lived `feature/*` branches off `dev_alm`), run the Streamlit frontend to manually verify
  nothing is broken, and only then merge `dev_alm → main`.
- Optional `feature/<epic>-<short-desc>` branches off `dev_alm` for larger issues; squash-merge back
  into `dev_alm`.

```
feature/* ──▶ dev_alm ──(verify via frontend + green CI)──▶ main
```

**Default working branch is `dev_alm`.** Never commit directly to `main`. Before promoting to `main`:
CI green, the Streamlit dashboard exercised, and the change verified end-to-end.

### Commits — Conventional Commits
`type(scope): summary` where `type ∈ {feat, fix, docs, refactor, test, chore, perf, ci, build}` and
`scope` is an epic/layer (`rule-engine`, `normalization`, `scraper`, `db`, `infra`, `api`…).
Example: `feat(rule-engine): add BETWEEN operator strategy`. Imperative mood, ≤72-char subject, body
explains *why*. Reference issues (`Closes #12`).

### PRs
Small and focused; description links the issue and states what was verified. CI (lint, mypy,
import-linter, tests) must pass. Merges to `main` only from `dev_alm`.

---

## 10. Documentation standards

- Architecture decisions → an ADR row in
  [decisions.md](docs/architecture/decisions.md); design changes update the relevant `0x-*.md`.
- Every design doc carries **Status / Owner / Depends on** and records the **rejected alternative**.
- Public domain concepts are documented where defined; keep this `CLAUDE.md` current when a
  convention changes — it is the source of truth loaded every session.
- Diagrams are **Mermaid** in Markdown (GitHub-rendered), not binary images.

---

## 11. Logging conventions

- **`structlog`**, JSON in production, key-value in dev. No `print`.
- A **correlation id per alert cycle** threads through planner → scrape → normalize → evaluate →
  enqueue for traceability.
- Log **events with context** (`portal_slug`, `external_id`, `signature`, counts), not prose.
- **Never log secrets or full PII.** Normalization issues, `SearchExecution` outcomes, and
  circuit-breaker state changes are logged at the appropriate level (warn/error).
- Levels: `DEBUG` dev detail · `INFO` lifecycle events · `WARNING` recoverable/degraded (unmapped
  vocab, retry) · `ERROR` failed operation · `CRITICAL` process-threatening.

---

## 12. Error handling strategy

- **Domain** raises typed domain errors (`InvalidConditionError`, `DomainError` subclasses); it never
  raises framework/HTTP exceptions.
- **Infrastructure** catches external failures (HTTP, parse, DB) and either retries (`tenacity` with
  backoff) or wraps them in a domain-meaningful error at the port boundary.
- **Isolation:** one portal/scraper failing fails only its `SearchExecution` and is circuit-broken;
  the alert cycle continues (driver D7).
- **Idempotency:** matches (`UNIQUE(alert_id, property_id)`) and outbox entries are idempotent — a
  retried cycle never double-notifies.
- Fail **loud in dev, safe in prod**: validate at boundaries; never silently swallow (unmapped data
  becomes an `OTHER`/`UNKNOWN` value **plus** a logged issue, never a dropped listing).

---

## 13. Performance considerations

- The cost model scales with **distinct searches**, not users or alerts — protect the dedup
  (signature + `SearchCache`) whenever touching the planner.
- Push coarse filters to the portal (server-side) to shrink downloads; do precise filtering
  client-side in the Rule Engine.
- Only write `PriceHistory` on price change; use `content_hash` to skip re-normalizing unchanged
  listings.
- Indexes exist for the hot paths (due-alert scan, pushable pre-filter, outbox poll) — see
  [03-database.md](docs/architecture/03-database.md); add an index with a stated query, not
  speculatively.
- Respect per-portal rate limits and politeness; the limiter/breaker are correctness features, not
  optional.

---

## 14. Security considerations

- Respect portal **robots/ToS** and legal constraints; be a polite scraper (rate limit, backoff,
  identify sensibly). Do not build detection-evasion for abusive scraping.
- **Secrets** (Telegram tokens, future DB creds) come from environment / `.env` (git-ignored); the
  repo ships `.env.example` only. Channel secrets are **encrypted at rest**.
- **Validate all input at boundaries** (Pydantic DTOs, VO constructors).
- Multi-tenant: queries are always scoped by `user_id`; never expose another user's alerts/matches.
- Principle of least privilege for any deployment credentials; keep dependencies patched
  (Dependabot).

---

## 15. Future roadmap (summary)

Phased plan in [docs/roadmap.md](docs/roadmap.md): Phase 1 foundation → 2 domain/persistence → 3 Rule
Engine → 4 Normalization → 5 Idealista + search planning → 6 Telegram → 7 scheduler **(MVP)** → 8
Streamlit dashboard. **V2:** more portals, cross-portal dedup, FastAPI, more channels, PostgreSQL,
query widening. **V3:** multi-user, full boolean UI, price-trend alerts, geo filters, observability.

---

## 16. Quick reference for a new session

1. Read [docs/architecture/README.md](docs/architecture/README.md) and this file.
2. Check the current **phase** in [docs/roadmap.md](docs/roadmap.md) and open GitHub issues.
3. Work on **`dev_alm`** (or a `feature/*` off it). Keep the dependency rule intact.
4. New filter → register a `FieldDescriptor` (doc 04). New portal → add a co-located scraper +
   normalizer + mapping tables + fixtures (docs 05, 07). New channel → add a `Notifier` adapter.
5. Write tests (unit-first). Run `ruff`, `black`, `mypy`, `import-linter`, `pytest` before committing.
6. Conventional-commit; verify via the Streamlit frontend; merge to `main` only when green + verified.
