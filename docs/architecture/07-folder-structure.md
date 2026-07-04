# 07 — Project & Folder Structure

> Status: **Accepted** · Owner: Architecture · Depends on: [01-architecture.md](01-architecture.md)

The layout maps **one-to-one onto the clean-architecture layers** (doc 01). Import direction is
enforced in CI by `import-linter`: `presentation → application → domain` and
`infrastructure → domain`, with **nothing importing into `domain`** except the standard library.

```
real_estate_tracker/
├── pyproject.toml              # deps, tool config (ruff, black, mypy, pytest, import-linter)
├── README.md
├── CLAUDE.md                   # how this repo must evolve (root, always-loaded)
├── .pre-commit-config.yaml
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
│
├── src/
│   └── real_estate/            # the installable package (src-layout)
│       │
│       ├── domain/             # ── INNER CORE · framework-free · no I/O ──
│       │   ├── model/          # entities + value objects (Property, SearchAlert, Money, Area…)
│       │   ├── vocabulary/     # controlled enums (PropertyType, LandType, Province/INE…)
│       │   ├── rules/          # Specification, composites, FieldRegistry, operator strategies
│       │   ├── services/       # pure domain services (AlertEngine, fingerprinting later)
│       │   ├── ports/          # abstract interfaces: Scraper, Normalizer, Notifier, *Repository, UnitOfWork
│       │   └── errors.py       # typed domain exceptions
│       │
│       ├── application/        # ── USE CASES · orchestration · owns transactions ──
│       │   ├── use_cases/      # RunAlertCycle, CreateAlert, DispatchNotifications, …
│       │   ├── dto/            # Pydantic DTOs crossing the boundary
│       │   ├── services/       # SearchPlanner (pushable/client split, signature, dedup)
│       │   └── ports.py        # application-level ports (Clock, IdGenerator…) if needed
│       │
│       ├── infrastructure/     # ── ADAPTERS · concrete implementations of domain ports ──
│       │   ├── persistence/
│       │   │   ├── models/     # SQLAlchemy ORM tables
│       │   │   ├── repositories/  # *Repository implementations
│       │   │   ├── unit_of_work.py
│       │   │   └── migrations/ # Alembic versions
│       │   ├── scrapers/       # BaseScraper + IdealistaScraper, FotocasaScraper, … (+ http/playwright clients)
│       │   ├── normalizers/    # per-portal Normalizer + mapping/vocabulary tables (Python dicts)
│       │   ├── notifications/  # TelegramNotifier (+ future EmailNotifier…), channel registry
│       │   ├── scheduling/     # APScheduler wiring, planner job, rate limiter, circuit breaker
│       │   ├── config/         # pydantic-settings, portal capabilities config
│       │   └── logging.py      # structlog setup
│       │
│       ├── presentation/       # ── ENTRY POINTS · thin ──
│       │   ├── cli/            # Typer CLI (MVP): create-alert, run-cycle, list-matches…
│       │   ├── api/            # FastAPI routers (future)
│       │   └── web/            # Streamlit dashboard (future)
│       │
│       ├── composition.py      # COMPOSITION ROOT · wires adapters → use cases (DI)
│       └── __main__.py         # process entry point
│
├── tests/
│   ├── unit/                   # domain + application, no I/O (mirrors src tree)
│   ├── integration/            # repositories, scrapers vs recorded fixtures, DB
│   ├── e2e/                    # full alert cycle against a seeded DB
│   └── fixtures/               # recorded RawListing samples per portal, golden Properties
│
├── docs/
│   ├── architecture/           # these design docs (00–07 + decisions)
│   ├── planning/               # GitHub Project mirror (epics/milestones/issues)
│   └── roadmap.md
│
└── scripts/                    # dev/ops helpers (seed db, backfill normalize, gh project setup)
```

## Responsibility of each area

| Path | Responsibility | May depend on |
|------|----------------|---------------|
| `domain/model` | Entities & value objects; invariants | stdlib only |
| `domain/vocabulary` | Controlled enums + INE data | stdlib only |
| `domain/rules` | Rule Engine (Specification, registry, operators) | `domain/*` |
| `domain/services` | Pure domain services (Alert Engine) | `domain/*` |
| `domain/ports` | Abstract interfaces the outer layers implement | `domain/*` |
| `application/use_cases` | Orchestrate a workflow end-to-end | `domain/*` |
| `application/services` | Search planning: split, signature, dedup | `domain/*` |
| `application/dto` | Boundary data shapes (Pydantic) | `domain/*` |
| `infrastructure/persistence` | ORM, repositories, UoW, migrations | `domain/ports`, `application` |
| `infrastructure/scrapers` | Portal scrapers → `RawListing` | `domain/ports` |
| `infrastructure/normalizers` | `RawListing` → `Property` + mapping tables | `domain/*` |
| `infrastructure/notifications` | Channel adapters + registry | `domain/ports` |
| `infrastructure/scheduling` | APScheduler jobs, rate limiting, breaker | `application` |
| `infrastructure/config` | Settings, portal capabilities | — |
| `presentation/*` | Entry points; parse input, call a use case | `application` |
| `composition.py` | The only module that imports every concrete adapter (DI wiring) | everything |
| `tests/*` | Mirrors `src`; unit tests never touch I/O | — |

## Conventions

- **src-layout** (`src/real_estate/`) so tests run against the installed package, catching packaging
  mistakes early.
- **One aggregate per module** in `domain/model`; VOs grouped by concept.
- **Ports live in the domain**, implementations in infrastructure — the physical expression of the
  dependency-inversion principle.
- **`tests/` mirrors `src/`** path-for-path so a reader finds the test for any module instantly.
- Portal-specific code (scraper + normalizer + mapping tables) is **co-located per portal** so adding
  a portal is an additive, localized change (OCP).
