#!/usr/bin/env bash
set -uo pipefail
REPO="alopezmoreira1989/real_estate_tracker"

echo "=== Labels ==="
mklabel() { gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force >/dev/null 2>&1 && echo "  label: $1"; }

# Epics
mklabel "epic:arch"          "0E8A16" "Architecture & clean-code foundation"
mklabel "epic:db"            "5319E7" "Database, models, migrations, repositories"
mklabel "epic:rule-engine"   "B60205" "Alert & Rule Engine (Specification)"
mklabel "epic:normalization" "1D76DB" "RawListing -> canonical Property"
mklabel "epic:scrapers"      "FBCA04" "Portal scrapers"
mklabel "epic:notifications" "0052CC" "Notification channels & dispatch"
mklabel "epic:scheduler"     "006B75" "Scheduling, dedup orchestration"
mklabel "epic:api"           "C2E0C6" "FastAPI (future)"
mklabel "epic:frontend"      "D93F0B" "Streamlit / UI"
mklabel "epic:deploy"        "BFDADC" "Docker, CI/CD"
mklabel "epic:testing"       "0E8A16" "Test suites & fixtures"
mklabel "epic:docs"          "CCCCCC" "Documentation"
mklabel "epic:perf"          "FEF2C0" "Performance & scale"
# Type
mklabel "type:feature" "A2EEEF" "New capability"
mklabel "type:infra"   "BFD4F2" "Tooling / infrastructure"
mklabel "type:test"    "D4C5F9" "Testing work"
mklabel "type:chore"   "EDEDED" "Chore / maintenance"
# Complexity
mklabel "complexity:S" "C2E0C6" "<= half a day"
mklabel "complexity:M" "FBCA04" "1-2 days"
mklabel "complexity:L" "D93F0B" "3-5 days"
# Priority
mklabel "priority:mvp" "B60205" "Required for MVP"

echo "=== Milestones ==="
mkms() { gh api "repos/$REPO/milestones" -f title="$1" -f description="$2" >/dev/null 2>&1 && echo "  milestone: $1" || echo "  milestone exists/skip: $1"; }
mkms "Phase 1: Foundation & Tooling"       "Professional skeleton that enforces the architecture."
mkms "Phase 2: Domain & Persistence"       "Canonical model, vocabularies, SQLAlchemy + repositories."
mkms "Phase 3: Rule Engine"                "Specification-based alert evaluation."
mkms "Phase 4: Normalization"              "RawListing to canonical Property."
mkms "Phase 5: Idealista Scraper & Search" "First scraper + search dedup planning."
mkms "Phase 6: Telegram Notifications"     "Outbox + Telegram delivery."
mkms "Phase 7: Scheduler (MVP)"            "Unattended scheduled operation. MVP complete."
mkms "Phase 8: Frontend (Dashboard)"       "Streamlit verification dashboard on dev_alm."
mkms "V2: Breadth & Robustness"            "More portals, dedup, FastAPI, Postgres."
mkms "V3: Product & Scale"                 "Multi-user, boolean UI, price-trend alerts."

echo "=== Issues ==="
ci() { # title, milestone, labels, body
  local url
  url=$(gh issue create --repo "$REPO" --title "$1" --milestone "$2" --label "$3" --body "$4" 2>&1)
  echo "  $url"
}

# ---------- Phase 1 ----------
ci "Scaffold clean-architecture package skeleton" "Phase 1: Foundation & Tooling" "epic:arch,type:infra,complexity:M,priority:mvp" \
"**Description**: Create the src-layout package \`src/real_estate/\` with domain/application/infrastructure/presentation packages and empty \`__init__.py\` per doc 07.

**Acceptance Criteria**
- [ ] Package importable as \`real_estate\`
- [ ] Layer folders exist matching docs/architecture/07-folder-structure.md
- [ ] \`composition.py\` + \`__main__.py\` placeholders present

**Dependencies**: none
**Complexity**: M  ·  **Order**: 1"

ci "Configure tooling: ruff, black, mypy(strict), pytest, import-linter" "Phase 1: Foundation & Tooling" "epic:arch,type:infra,complexity:M,priority:mvp" \
"**Description**: Configure \`pyproject.toml\` with all quality tools and import-linter contracts enforcing the dependency rule (domain imports stdlib only).

**Acceptance Criteria**
- [ ] \`ruff\`, \`black\`, \`mypy --strict\`, \`pytest\` run locally
- [ ] import-linter contracts encode layer boundaries (doc CLAUDE.md §6)
- [ ] A deliberate boundary violation fails import-linter

**Dependencies**: #1
**Complexity**: M  ·  **Order**: 2"

ci "Pre-commit hooks, .env.example, structlog logging setup" "Phase 1: Foundation & Tooling" "epic:arch,type:infra,complexity:S,priority:mvp" \
"**Description**: Add pre-commit config (ruff/black/mypy), \`.env.example\`, and structlog configuration per CLAUDE.md §11.

**Acceptance Criteria**
- [ ] \`pre-commit run --all-files\` passes
- [ ] structlog emits JSON in prod / key-value in dev
- [ ] \`.env.example\` documents required vars, no secrets committed

**Dependencies**: #2
**Complexity**: S  ·  **Order**: 3"

ci "GitHub Actions CI pipeline" "Phase 1: Foundation & Tooling" "epic:deploy,type:infra,complexity:M,priority:mvp" \
"**Description**: CI running lint + mypy + import-linter + tests on push and PR to dev_alm/main.

**Acceptance Criteria**
- [ ] Workflow triggers on PR to dev_alm and main
- [ ] All checks required to pass before merge
- [ ] Coverage reported

**Dependencies**: #2
**Complexity**: M  ·  **Order**: 4"

ci "Dockerfile and docker-compose (app + Postgres service)" "Phase 1: Foundation & Tooling" "epic:deploy,type:infra,complexity:M" \
"**Description**: Containerize the app; compose file with app and a (future) Postgres service.

**Acceptance Criteria**
- [ ] \`docker build\` succeeds
- [ ] \`docker compose up\` starts the app container
- [ ] Postgres service defined but MVP still uses SQLite volume

**Dependencies**: #1
**Complexity**: M  ·  **Order**: 5"

# ---------- Phase 2 ----------
ci "Value objects: Money, Area, PricePerM2, Location, GeoPoint, Features, Media" "Phase 2: Domain & Persistence" "epic:db,type:feature,complexity:M,priority:mvp" \
"**Description**: Implement immutable, unit-safe value objects per doc 02 with validation.

**Acceptance Criteria**
- [ ] Frozen dataclasses; invariants enforced in constructors
- [ ] Money arithmetic only within same currency
- [ ] Tri-state features (bool|None); unit tests for edges

**Dependencies**: #1
**Complexity**: M  ·  **Order**: 6"

ci "Controlled vocabularies + INE province/municipality data" "Phase 2: Domain & Persistence" "epic:db,type:feature,complexity:M,priority:mvp" \
"**Description**: Enums (ListingType, PropertyType, LandType, Status) and INE-keyed Province/Municipality data (doc 02 §3).

**Acceptance Criteria**
- [ ] All 52 provinces keyed by INE code
- [ ] Municipality belongs to exactly one province (validated)
- [ ] OTHER/UNKNOWN members present

**Dependencies**: #1
**Complexity**: M  ·  **Order**: 7"

ci "Property entity + SearchAlert aggregate (condition tree)" "Phase 2: Domain & Persistence" "epic:db,type:feature,complexity:M,priority:mvp" \
"**Description**: Canonical Property entity and SearchAlert aggregate owning the RuleGroup/AlertCondition tree (doc 02 §2, §4).

**Acceptance Criteria**
- [ ] SearchAlert enforces >=1 condition and valid field/operator at construction
- [ ] Condition edits go through the aggregate root
- [ ] price_per_m2 derived property computed from VOs

**Dependencies**: #6, #7
**Complexity**: M  ·  **Order**: 8"

ci "Domain ports: repositories, Scraper, Normalizer, Notifier, UnitOfWork" "Phase 2: Domain & Persistence" "epic:arch,type:feature,complexity:S,priority:mvp" \
"**Description**: Define abstract ports in the domain layer (doc 01, 07).

**Acceptance Criteria**
- [ ] Protocols/ABCs for each port, no framework imports
- [ ] import-linter confirms domain purity

**Dependencies**: #8
**Complexity**: S  ·  **Order**: 9"

ci "SQLAlchemy models for all tables + Alembic baseline migration" "Phase 2: Domain & Persistence" "epic:db,type:feature,complexity:L,priority:mvp" \
"**Description**: ORM models for every table in doc 03 with keys, indexes, constraints; Alembic baseline.

**Acceptance Criteria**
- [ ] All tables, FKs, UNIQUE and CHECK constraints from doc 03
- [ ] Hot-path indexes present
- [ ] \`alembic upgrade head\` creates schema on SQLite

**Dependencies**: #9
**Complexity**: L  ·  **Order**: 10"

ci "Repository + UnitOfWork implementations (SQLite) + integration tests" "Phase 2: Domain & Persistence" "epic:db,type:feature,complexity:L,priority:mvp" \
"**Description**: SQLAlchemy adapters implementing the domain repository/UoW ports, with mapping between ORM and domain objects.

**Acceptance Criteria**
- [ ] CRUD for SearchAlert and Property round-trips domain <-> DB
- [ ] UoW commits/rolls back as one transaction
- [ ] Integration tests against a temp SQLite DB

**Dependencies**: #10
**Complexity**: L  ·  **Order**: 11"

# ---------- Phase 3 ----------
ci "Specification base + And/Or/Not composites" "Phase 3: Rule Engine" "epic:rule-engine,type:feature,complexity:S,priority:mvp" \
"**Description**: Specification protocol and composite combinators (doc 04 §2).

**Acceptance Criteria**
- [ ] is_satisfied_by contract
- [ ] Truth-table tests for AND/OR/NOT nesting

**Dependencies**: #8
**Complexity**: S  ·  **Order**: 12"

ci "FieldRegistry + FieldDescriptors for MVP fields" "Phase 3: Rule Engine" "epic:rule-engine,type:feature,complexity:M,priority:mvp" \
"**Description**: Registry mapping canonical field keys to type/accessor/allowed-operators (doc 04 §3).

**Acceptance Criteria**
- [ ] Descriptors for province, property_type, land_type, price, price_per_m2, area, rooms, description, features.*
- [ ] Adding a field requires only a registration
- [ ] Attribute escape-hatch fields registerable

**Dependencies**: #12
**Complexity**: M  ·  **Order**: 13"

ci "Operator strategies (EQ..BETWEEN, IN, CONTAINS with accent-folding)" "Phase 3: Rule Engine" "epic:rule-engine,type:feature,complexity:M,priority:mvp" \
"**Description**: Pure comparison strategies per doc 04 §4, including accent/case-insensitive CONTAINS for Spanish text.

**Acceptance Criteria**
- [ ] All operators implemented with table-driven tests
- [ ] CONTAINS folds accents (agua == água)
- [ ] Operator/field-type validity enforced

**Dependencies**: #13
**Complexity**: M  ·  **Order**: 14"

ci "SpecificationFactory: persisted condition tree -> Specification" "Phase 3: Rule Engine" "epic:rule-engine,type:feature,complexity:M,priority:mvp" \
"**Description**: Recursively build a Specification from a SearchAlert's tree (doc 04 §5).

**Acceptance Criteria**
- [ ] Round-trip: tree -> spec -> evaluation
- [ ] Unknown field/operator raises InvalidConditionError

**Dependencies**: #13, #14
**Complexity**: M  ·  **Order**: 15"

ci "AlertEngine.evaluate + idempotent AlertMatch creation" "Phase 3: Rule Engine" "epic:rule-engine,type:feature,complexity:M,priority:mvp" \
"**Description**: Evaluate an alert against candidate properties; produce matches deduped by UNIQUE(alert_id, property_id) (doc 04 §6).

**Acceptance Criteria**
- [ ] Returns candidate matches; persistence is idempotent
- [ ] Re-running the same candidates produces no duplicate notifications

**Dependencies**: #15, #11
**Complexity**: M  ·  **Order**: 16"

ci "Rule Engine test suite + 'Urbanizable land in Pontevedra' golden fixture" "Phase 3: Rule Engine" "epic:testing,type:test,complexity:M,priority:mvp" \
"**Description**: Comprehensive tests incl. Hypothesis algebraic laws and the flagship golden alert.

**Acceptance Criteria**
- [ ] Golden fixture (province=36, LAND/URBANIZABLE, price/m2<=20, area>=3000, contains 'water', not 'occupied') passes end-to-end
- [ ] Property-based test: NOT(spec) satisfied iff spec not

**Dependencies**: #16
**Complexity**: M  ·  **Order**: 17"

# ---------- Phase 4 ----------
ci "RawListing + NormalizationResult/Issue types" "Phase 4: Normalization" "epic:normalization,type:feature,complexity:S,priority:mvp" \
"**Description**: Define the raw capture DTO and normalization result/issue types (doc 05 §1).

**Acceptance Criteria**
- [ ] RawListing carries portal_id, external_id, url, scraped_at, raw dict
- [ ] NormalizationResult carries Property|None + issues list

**Dependencies**: #8
**Complexity**: S  ·  **Order**: 18"

ci "Shared Spanish-locale parsers (money, area, int)" "Phase 4: Normalization" "epic:normalization,type:feature,complexity:M,priority:mvp" \
"**Description**: Robust parsers for '120.000 €', '3.000 m²', '1.234,56' (doc 05 §2).

**Acceptance Criteria**
- [ ] Handles Spanish thousands/decimal separators and currency symbols
- [ ] Never uses naive float(str); unit tests for edge/empty values

**Dependencies**: #6
**Complexity**: M  ·  **Order**: 19"

ci "NormalizerRegistry + base normalizer composition (4 steps)" "Phase 4: Normalization" "epic:normalization,type:feature,complexity:M,priority:mvp" \
"**Description**: Registry to select normalizer by portal + base composition (field map -> parse -> vocab -> derive) per doc 05 §2-§4.

**Acceptance Criteria**
- [ ] Portals self-register; no central switch
- [ ] Base normalizer runs the four ordered steps and assembles Property

**Dependencies**: #18, #19
**Complexity**: M  ·  **Order**: 20"

ci "Vocabulary dictionaries (property/land type, province->INE) as Python dicts" "Phase 4: Normalization" "epic:normalization,type:feature,complexity:M,priority:mvp" \
"**Description**: Typed dict mapping tables per ADR-015 (doc 05 §3).

**Acceptance Criteria**
- [ ] Coverage tests: known portal terms map to non-OTHER canonical values
- [ ] Unknown values map to OTHER/UNKNOWN + emit an issue (never dropped)

**Dependencies**: #7, #20
**Complexity**: M  ·  **Order**: 21"

ci "Normalization golden-fixture tests (recorded RawListings)" "Phase 4: Normalization" "epic:testing,type:test,complexity:M" \
"**Description**: Store sanitized recorded RawListings and assert exact canonical Property output.

**Acceptance Criteria**
- [ ] Fixtures in tests/fixtures per portal
- [ ] Deterministic RawListing -> Property assertions

**Dependencies**: #20, #21
**Complexity**: M  ·  **Order**: 22"

# ---------- Phase 5 ----------
ci "BaseScraper + httpx client, rate limiter, tenacity retry, circuit breaker" "Phase 5: Idealista Scraper & Search" "epic:scrapers,type:feature,complexity:M,priority:mvp" \
"**Description**: Base scraper infrastructure with politeness controls (doc 06 §5, D7).

**Acceptance Criteria**
- [ ] Token-bucket rate limiter per portal
- [ ] Retry with backoff; circuit breaker opens after N failures
- [ ] BaseScraper interface returns RawListing objects

**Dependencies**: #9
**Complexity**: M  ·  **Order**: 23"

ci "IdealistaScraper -> RawListing (BeautifulSoup; Playwright only if required)" "Phase 5: Idealista Scraper & Search" "epic:scrapers,type:feature,complexity:L,priority:mvp" \
"**Description**: First concrete scraper per ADR-004.

**Acceptance Criteria**
- [ ] Produces RawListing without cleaning
- [ ] Respects rate limits/robots
- [ ] Contract test vs recorded HTML fixture

**Dependencies**: #23
**Complexity**: L  ·  **Order**: 24"

ci "Portal capabilities config (pushable fields, rate limits)" "Phase 5: Idealista Scraper & Search" "epic:scheduler,type:feature,complexity:S,priority:mvp" \
"**Description**: Declarative capabilities per portal used by the SearchPlanner (doc 03 portal.capabilities, doc 06 §1).

**Acceptance Criteria**
- [ ] Idealista capabilities declare server-side filterable fields + limits
- [ ] Read by application layer, not hardcoded in planner

**Dependencies**: #24
**Complexity**: S  ·  **Order**: 25"

ci "SearchPlanner: split pushable/client-side, canonical signature, dedup" "Phase 5: Idealista Scraper & Search" "epic:scheduler,type:feature,complexity:M,priority:mvp" \
"**Description**: Turn due alerts into the fewest portal queries (doc 06 §1-§3).

**Acceptance Criteria**
- [ ] Conditions split by capabilities into pushable vs client-side
- [ ] Canonical signature is identical for equivalent searches (incl. cross-user)
- [ ] Ten alerts on Pontevedra -> one scrape

**Dependencies**: #25, #15
**Complexity**: M  ·  **Order**: 26"

ci "SearchCache + SearchExecution write path; property upsert + PriceHistory" "Phase 5: Idealista Scraper & Search" "epic:scheduler,type:feature,complexity:M,priority:mvp" \
"**Description**: Cache results by signature with TTL; record executions; upsert PortalListing/Property; append PriceHistory on change (doc 06 §4).

**Acceptance Criteria**
- [ ] Cache hit within TTL skips scrape
- [ ] PriceHistory row only on price change
- [ ] content_hash skips re-normalizing unchanged listings

**Dependencies**: #11, #26
**Complexity**: M  ·  **Order**: 27"

ci "RunAlertCycle use-case wiring the full pipeline" "Phase 5: Idealista Scraper & Search" "epic:scheduler,type:feature,complexity:L,priority:mvp" \
"**Description**: Orchestrate plan -> fetch/cache -> normalize -> evaluate -> enqueue (doc 08 §2).

**Acceptance Criteria**
- [ ] Running a cycle scrapes Idealista once per signature and creates AlertMatches
- [ ] Scraper failure isolated; cycle continues (doc 08 §4)
- [ ] e2e test on a seeded DB

**Dependencies**: #16, #20, #27
**Complexity**: L  ·  **Order**: 28"

# ---------- Phase 6 ----------
ci "Notification outbox persistence + NotificationChannel (Telegram)" "Phase 6: Telegram Notifications" "epic:notifications,type:feature,complexity:M,priority:mvp" \
"**Description**: Outbox table write path and user Telegram channel with encrypted secrets (doc 03, 08 §3).

**Acceptance Criteria**
- [ ] New matches enqueue PENDING notifications
- [ ] Channel secrets encrypted at rest
- [ ] Idempotent enqueue (no duplicates)

**Dependencies**: #28
**Complexity**: M  ·  **Order**: 29"

ci "TelegramNotifier adapter + message formatting" "Phase 6: Telegram Notifications" "epic:notifications,type:feature,complexity:M,priority:mvp" \
"**Description**: Implement the Notifier port for Telegram.

**Acceptance Criteria**
- [ ] Sends a formatted listing message (title, price, area, link)
- [ ] Errors surface for retry; unit test with a fake client

**Dependencies**: #29
**Complexity**: M  ·  **Order**: 30"

ci "Dispatcher job: poll outbox, send, retry/backoff, honor frequency" "Phase 6: Telegram Notifications" "epic:notifications,type:feature,complexity:M,priority:mvp" \
"**Description**: Separate dispatch loop decoupled from scraping (doc 08 §3).

**Acceptance Criteria**
- [ ] PENDING -> SENT on success; attempts/last_error on failure
- [ ] Respects per-alert frequency and per-channel rate limits
- [ ] New matching listing -> Telegram message end-to-end

**Dependencies**: #30
**Complexity**: M  ·  **Order**: 31"

# ---------- Phase 7 ----------
ci "APScheduler planner job (due-set) + dispatcher scheduling" "Phase 7: Scheduler (MVP)" "epic:scheduler,type:feature,complexity:M,priority:mvp" \
"**Description**: Recurring planner loads due alerts via the hot index and dispatches scrapes; dispatcher scheduled separately (doc 06 §5).

**Acceptance Criteria**
- [ ] Single planner job, not one timer per alert
- [ ] Due-set query uses (is_active, last_run_at) index
- [ ] Runs unattended

**Dependencies**: #28, #31
**Complexity**: M  ·  **Order**: 32"

ci "Coalescing, jitter, per-portal worker pools" "Phase 7: Scheduler (MVP)" "epic:scheduler,type:feature,complexity:M" \
"**Description**: In-flight coalescing so duplicate signatures attach to a running scrape; jitter; concurrency caps per portal (doc 06 §5-§6).

**Acceptance Criteria**
- [ ] Concurrent identical signatures share one scrape
- [ ] Per-portal concurrency cap enforced

**Dependencies**: #32
**Complexity**: M  ·  **Order**: 33"

ci "Operational CLI (Typer): run-cycle, alerts, list-matches, channels" "Phase 7: Scheduler (MVP)" "epic:frontend,type:feature,complexity:M,priority:mvp" \
"**Description**: Presentation-layer CLI to operate the platform (doc 07).

**Acceptance Criteria**
- [ ] Create/list alerts, list recent matches, manage channels, trigger a cycle
- [ ] Thin: delegates to application use-cases

**Dependencies**: #28, #29
**Complexity**: M  ·  **Order**: 34"

# ---------- Phase 8 ----------
ci "Streamlit dashboard: alerts CRUD, matches, execution & normalization health" "Phase 8: Frontend (Dashboard)" "epic:frontend,type:feature,complexity:L" \
"**Description**: Dev-facing verification UI (doc roadmap Phase 8).

**Acceptance Criteria**
- [ ] Create/edit alerts; view recent matches
- [ ] SearchExecution health + normalization-issue rate visible
- [ ] Runs against the same application layer

**Dependencies**: #34
**Complexity**: L  ·  **Order**: 35"

ci "Frontend-based verification workflow on dev_alm before merge to main" "Phase 8: Frontend (Dashboard)" "epic:docs,type:chore,complexity:S" \
"**Description**: Document and script the verify-on-dev_alm-then-merge flow (CLAUDE.md §9).

**Acceptance Criteria**
- [ ] Documented steps: run dashboard on dev_alm, verify, merge to main
- [ ] Optional helper script in scripts/

**Dependencies**: #35
**Complexity**: S  ·  **Order**: 36"

echo "=== Done ==="
