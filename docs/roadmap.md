# Development Roadmap

Phased plan from empty repo to MVP, then v2 / v3. Each phase is a **milestone** in the GitHub
Project; issues within a phase carry an **epic** label. Order is dependency-driven — later phases
assume earlier ones. Complexity: **S** (≤½ day) · **M** (1–2 days) · **L** (3–5 days).

Legend for epics: `arch` `db` `rule-engine` `normalization` `scrapers` `notifications` `scheduler`
`api` `frontend` `deploy` `testing` `docs` `perf`.

---

## Phase 1 — Foundation & tooling  *(epics: arch, docs, deploy, testing)*

Goal: a professional skeleton that enforces the architecture.

- Scaffold `src/real_estate/` clean-architecture packages (empty layers + `__init__`). **M**
- `pyproject.toml`: ruff, black, mypy (strict), pytest, coverage, **import-linter** boundary rules. **M**
- Pre-commit hooks; `.env.example`; `structlog` logging setup. **S**
- GitHub Actions CI: lint + type-check + test + import-linter on push/PR. **M**
- Dockerfile + docker-compose (app + future Postgres). **M**
- `CLAUDE.md`, this roadmap, and architecture docs committed. **S**

**Exit:** CI green on an empty-but-wired skeleton; boundaries enforced.

---

## Phase 1.5 — Project hardening  *(epics: arch, docs, testing, deploy)* — ✅ **Complete**

Goal: make the repository itself production-quality — documentation, architecture decision records,
developer experience, and CI/tooling polish only. This phase itself added no entities, repositories,
ORM models, scrapers, or business logic. It was carried out while Phase 2 (Domain & Persistence) was
being merged and Phase 3 (Rule Engine) was independently developed on `dev_alm`; this phase's own
scope stayed strictly non-functional regardless.

- Split `docs/architecture/decisions.md` into 17 individual ADRs under `docs/architecture/adr/`
  (7 newly documented foundational decisions + 10 prior decisions preserved and renumbered), with
  every cross-reference in `CLAUDE.md`, this roadmap, and `scripts/gh_setup.sh` updated to match.
- Added system diagrams (`09-diagrams.md`) and an architectural risk/future-proofing assessment
  (`10-future-proofing.md`) for new portals, notification channels, a REST API, a web UI, auth,
  Docker/cloud deployment, and multi-user support.
- Rewrote the root `README.md` as a full project overview; added `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `DEVELOPMENT.md`, and an MIT `LICENSE`.
- Hardened `import-linter`: added a contract forbidding the domain from importing third-party
  frameworks directly (not just internal layers), with every contract's rationale documented inline
  in `pyproject.toml`.
- Added GitHub issue templates (bug/feature/question) and a pull request template; expanded
  `docs/planning/README.md` with full label documentation, a Project-board usage guide, and the
  release process.
- Commented `pyproject.toml` and `.pre-commit-config.yaml` tool configuration; fixed CI's pip
  caching (`cache-dependency-path`) and split workflow steps for per-tool failure attribution.
- Repository polish: confirmed every placeholder package is roadmap-justified, tightened
  `.gitignore` (import-linter cache, local Claude Code state).

**Exit:** all quality gates (ruff/black/mypy --strict/import-linter/pytest) green; every
documentation cross-reference verified to resolve; no business logic introduced.

---

## Phase 2 — Domain core: model, vocabularies, persistence  *(epics: db, arch, testing)*

- Value objects: `Money`, `Area`, `PricePerM2`, `Location`, `GeoPoint`, `Features`, `Media`. **M**
- Controlled vocabularies + INE province/municipality data. **M**
- `Property` entity + `SearchAlert` aggregate (+ `RuleGroup`/`AlertCondition` tree). **M**
- Domain ports: repositories, `Scraper`, `Normalizer`, `Notifier`, `UnitOfWork`. **S**
- SQLAlchemy models for all tables (doc 03) + Alembic baseline migration. **L**
- Repository + UoW implementations (SQLite); repo integration tests. **L**

**Exit:** can persist/load alerts & properties; migrations run; unit + integration tests pass.

---

## Phase 3 — Rule Engine  *(epic: rule-engine)*

- `Specification` + `And/Or/Not` composites. **S**
- `FieldRegistry` + `FieldDescriptor`s for MVP fields. **M**
- Operator strategies (`EQ`…`BETWEEN`, `CONTAINS` with accent-folding). **M**
- `SpecificationFactory` (persisted tree → spec). **M**
- `AlertEngine.evaluate`; idempotent match creation. **M**
- Engine test suite incl. the "Urbanizable land in Pontevedra" golden fixture + Hypothesis laws. **M**

**Exit:** given properties + an alert, correct matches; new filters addable via registration only.

---

## Phase 4 — Normalization layer  *(epic: normalization)*

- `RawListing` + `NormalizationResult`/`NormalizationIssue`. **S**
- Shared parsers (Spanish locale money/area/int). **M**
- `NormalizerRegistry` + base normalizer composition (4 steps, doc 05). **M**
- Vocabulary dictionaries (property/land type, province→INE). **M**
- Recorded-fixture golden tests. **M**

**Exit:** a `RawListing` deterministically becomes a valid canonical `Property`.

---

## Phase 5 — First scraper (Idealista) + Search planning  *(epics: scrapers, scheduler)*

- `BaseScraper` + httpx client, rate limiter, `tenacity` retry, circuit breaker. **M**
- `IdealistaScraper` → `RawListing` (per [ADR-004](architecture/adr/004-playwright-for-scraping.md):
  BeautifulSoup; Playwright only if required). **L**
- Portal `capabilities` config (pushable fields, limits). **S**
- `SearchPlanner`: split pushable/client-side, canonical signature, dedup. **M**
- `SearchCache` + `SearchExecution` write path; property upsert + `PriceHistory`. **M**
- `RunAlertCycle` use-case wiring the whole pipeline. **L**

**Exit:** running a cycle scrapes Idealista once per signature and produces `AlertMatch`es.

---

## Phase 6 — Telegram notifications  *(epic: notifications)*

- Notification **outbox** persistence + `NotificationChannel` (Telegram). **M**
- `TelegramNotifier` adapter + message formatting. **M**
- Dispatcher job: poll pending, send, retry/backoff, honor frequency. **M**

**Exit:** a new matching listing produces a Telegram message end-to-end.

---

## Phase 7 — Scheduler & orchestration  *(epic: scheduler)*

- APScheduler planner job (due-set model) + dispatcher schedule. **M**
- Coalescing/jitter; per-portal worker pools. **M**
- Operational CLI: `run-cycle`, `list-matches`, `alerts`, `channels`. **M**

**Exit:** the platform runs unattended on a schedule for one user. **← MVP COMPLETE**

---

## Phase 8 — Minimal frontend (dev-facing)  *(epic: frontend)*

- Streamlit dashboard: alerts CRUD, recent matches, execution health, normalization-issue rate. **L**
- Runs on the **`dev_alm`** branch as the manual-verification surface before merging to `main`
  (see CLAUDE.md → Git workflow). **S**

**Exit:** a UI to create alerts and eyeball results/health.

---

## MVP definition of done

Single user; ≥1 portal (Idealista) scraped on schedule with dedup; alerts with arbitrary conditions
evaluated by the Rule Engine; Telegram notifications; CI/tests/lint green; Streamlit dashboard for
verification on `dev_alm`.

---

## Version 2 — breadth & robustness

- Additional scrapers: Fotocasa, Pisos.com, Habitaclia, Milanuncios (each = scraper + normalizer +
  mapping tables + fixtures). *(scrapers, normalization)*
- **Cross-portal dedup** enabled via `fingerprint` + backfill
  ([ADR-013](architecture/adr/013-defer-cross-portal-dedup.md)). *(db, perf)*
- **FastAPI** for programmatic alert management; auth scaffolding. *(api)*
- Email + Discord notifiers. *(notifications)*
- PostgreSQL migration; JSONB/GIN attribute indexes; FTS keyword push-down
  ([ADR-016](architecture/adr/016-keyword-contains-python-then-db-fts.md)). *(db, perf)*
- Query **widening/superset** dedup optimization (doc 06 §2). *(perf, scheduler)*

## Version 3 — product & scale

- Multi-user sign-up, per-user quotas & fairness (doc 06 §6). *(api, arch)*
- Full boolean condition builder in UI (OR/NOT groups —
  [ADR-014](architecture/adr/014-condition-tree-and-only-mvp-ui.md)). *(frontend, rule-engine)*
- Price-drop / market-trend alerts from `PriceHistory`; saved-search analytics. *(rule-engine, perf)*
- Geo radius filters (`WITHIN_RADIUS`), map view. *(rule-engine, frontend)*
- WhatsApp & push channels; notification digests. *(notifications)*
- Observability: metrics, tracing, alerting on portal breakage. *(perf, deploy)*

---

## Recommended implementation order (one line)

`Phase 1 → 1.5 → 2 → 3 → 4 → 5 → 6 → 7 (MVP) → 8 → V2 → V3`

Rule Engine (3) and Normalization (4) are independent of each other and can be parallelized after
Phase 2; both must precede Phase 5.
