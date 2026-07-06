# 09 — System Diagrams

> Status: **Accepted** · Owner: Architecture · Depends on: [01-architecture.md](01-architecture.md),
> [07-folder-structure.md](07-folder-structure.md)

Structural views of the system, complementing the runtime sequence diagrams in
[08-sequence-diagrams.md](08-sequence-diagrams.md). Added in Phase 1.5 to make the architecture's
shape visible at a glance, not just describable in prose.

---

## 1. System context

Who and what the platform talks to, at the coarsest level.

```mermaid
flowchart LR
    User(("User"))

    Platform["Real Estate Alert Platform\n(scrapes, normalizes, evaluates alerts, notifies)"]

    Idealista["Idealista"]
    Fotocasa["Fotocasa — V2"]
    OtherPortals["Pisos.com / Milanuncios / Habitaclia — V2"]
    Telegram["Telegram Bot API"]
    FutureChannels["Email / Discord — V2"]

    User -->|creates/edits alerts| Platform
    Platform -->|match notifications| User
    Platform -->|scrapes listings, rate-limited| Idealista
    Platform -.->|V2| Fotocasa
    Platform -.->|V2| OtherPortals
    Platform -->|sends match notifications| Telegram
    Platform -.->|V2| FutureChannels
```

The platform owns no user-facing surface of its own yet beyond a CLI (MVP) — everything the user
"sees" arrives via the notification channel. A REST API and web dashboard are V2/Phase 8 additions;
see [10-future-proofing.md](10-future-proofing.md).

---

## 2. Layered (Clean/Hexagonal) architecture

The dependency rule from [01-architecture.md](01-architecture.md) §3, as a diagram: arrows show the
*allowed* direction of source-code dependency. Nothing points into the domain from outside it.

```mermaid
flowchart TB
    subgraph Presentation["Presentation — entry points (thin)"]
        CLI["CLI (Typer) — MVP"]
        API["FastAPI — V2"]
        Web["Streamlit dashboard — Phase 8"]
    end

    subgraph Application["Application — orchestration, no I/O, no business rules"]
        UC["Use-cases\n(RunAlertCycle, CreateAlert, DispatchNotifications)"]
        Svc["Services\n(SearchPlanner)"]
        DTO["DTOs (Pydantic, boundary only)"]
    end

    subgraph Domain["Domain — the core, framework-free"]
        Model["Entities & Value Objects\n(Property, SearchAlert, Money, Area...)"]
        Rules["Rule Engine\n(Specification, FieldRegistry, Operators)"]
        Ports["Ports (Protocols)\n(Scraper, Normalizer, Notifier, *Repository, UnitOfWork)"]
    end

    subgraph Infrastructure["Infrastructure — adapters"]
        Persistence["Persistence\n(SQLAlchemy repos, UnitOfWork, Alembic)"]
        Scrapers["Scrapers\n(IdealistaScraper, ...)"]
        Normalizers["Normalizers\n(per portal)"]
        Notifications["Notifications\n(TelegramNotifier, ...)"]
        Scheduling["Scheduling\n(APScheduler, rate limiter, circuit breaker)"]
    end

    CLI --> UC
    API -.->|V2| UC
    Web -.->|Phase 8| UC

    UC --> Model
    UC --> Rules
    UC --> Ports
    Svc --> Ports
    UC --> Svc

    Persistence -.->|implements| Ports
    Scrapers -.->|implements| Ports
    Normalizers -.->|implements| Ports
    Notifications -.->|implements| Ports
    Scheduling --> UC

    classDef domain fill:#2b6cb0,color:#fff,stroke:#1a365d;
    classDef app fill:#38a169,color:#fff,stroke:#22543d;
    classDef infra fill:#dd6b20,color:#fff,stroke:#7b341e;
    classDef pres fill:#805ad5,color:#fff,stroke:#44337a;
    class Model,Rules,Ports domain
    class UC,Svc,DTO app
    class Persistence,Scrapers,Normalizers,Notifications,Scheduling infra
    class CLI,API,Web pres
```

Solid arrows are compile-time `import` dependencies (source code). Dashed arrows are *runtime*
relationships wired through dependency injection at the composition root — infrastructure adapters
never appear as an import inside application or domain code; they satisfy a `Port` `Protocol` and are
handed to a use-case by `composition.py`.

---

## 3. Dependency flow (what may import what)

The same rule, expressed as the exact contract enforced by import-linter
([ADR-006](adr/006-import-linter.md), `pyproject.toml` `[tool.importlinter]`).

```mermaid
flowchart LR
    presentation["presentation"] --> application["application"]
    application --> domain["domain"]
    infrastructure["infrastructure"] --> domain
    infrastructure -.->|"only where implementing\na use-case port"| application

    domain -.->|forbidden| application
    domain -.->|forbidden| infrastructure
    domain -.->|forbidden| presentation
    application -.->|forbidden| infrastructure
    application -.->|forbidden| presentation
    presentation -.->|forbidden| infrastructure
    infrastructure -.->|forbidden| presentation

    classDef allowed stroke:#38a169,stroke-width:2px;
    classDef forbidden stroke:#e53e3e,stroke-width:1px,stroke-dasharray: 4 2;
```

`composition.py` is deliberately outside this graph: it is the one module allowed to import
*every* concrete class (every adapter and every use-case) in order to wire them together. That
exemption is why it exists as a single, small, reviewable file rather than being implicit.

---

## 4. Clean Architecture (concentric view)

The traditional "onion" view of the same rule — dependencies always point toward the center.

```mermaid
flowchart TD
    subgraph Ring0[" "]
        direction TB
        Ring1["Infrastructure & Presentation (adapters, entry points)"]
        Ring2["Application (use-cases, orchestration)"]
        Ring3["Domain (entities, value objects, rule engine, ports)"]
    end
    Ring1 --> Ring2 --> Ring3
```

Read the arrows as "depends on." `Domain` sits at the center depending on nothing project-specific;
`Application` depends only on `Domain`; `Infrastructure`/`Presentation` depend on both inner rings
but never on each other directly (§3).

---

## 5. Package relationships (current, Phase 1 skeleton)

The actual `src/real_estate/` packages as they exist today (doc 07), and which ports each
infrastructure package will implement once Phase 2+ adds behavior.

```mermaid
flowchart TB
    subgraph domain["real_estate.domain"]
        d_model["model/"]
        d_vocab["vocabulary/"]
        d_rules["rules/"]
        d_services["services/"]
        d_ports["ports/"]
        d_errors["errors.py"]
    end

    subgraph application["real_estate.application"]
        a_uc["use_cases/"]
        a_dto["dto/"]
        a_svc["services/"]
        a_ports["ports.py"]
    end

    subgraph infrastructure["real_estate.infrastructure"]
        i_persist["persistence/ (models, repositories, unit_of_work.py)"]
        i_scrapers["scrapers/"]
        i_norm["normalizers/"]
        i_notif["notifications/"]
        i_sched["scheduling/"]
        i_config["config/ (settings.py)"]
        i_log["logging.py"]
    end

    subgraph presentation["real_estate.presentation"]
        p_cli["cli/"]
        p_api["api/"]
        p_web["web/"]
    end

    comp["composition.py"]
    main["__main__.py"]

    a_uc --> d_model
    a_uc --> d_rules
    a_uc --> d_ports
    a_svc --> d_ports

    i_persist -.->|implements *Repository, UnitOfWork| d_ports
    i_scrapers -.->|implements Scraper| d_ports
    i_norm -.->|implements Normalizer| d_ports
    i_notif -.->|implements Notifier| d_ports

    p_cli --> a_uc

    comp --> i_persist
    comp --> i_scrapers
    comp --> i_norm
    comp --> i_notif
    comp --> i_sched
    comp --> p_cli
    comp --> a_uc
    main --> comp
```

Every `i_*` package box is currently an empty placeholder (Phase 1) — this diagram is the map Phase 2
onward fills in, package by package, without changing its shape.

---

## 6. Future deployment (V2 target)

The MVP runs as a single process (CLI + scheduler) against SQLite on one machine. This is the
target shape once the roadmap's V2 items (FastAPI, PostgreSQL, multiple portals) land — **nothing
here is built yet**; see [10-future-proofing.md](10-future-proofing.md) for what today's design does
to keep this reachable without a rewrite.

```mermaid
flowchart TB
    subgraph Client
        Browser["Web dashboard (browser)"]
        TelegramApp["Telegram app"]
    end

    subgraph Deployment["Application host(s)"]
        API["FastAPI (presentation/api)"]
        Scheduler["Scheduler worker\n(planner + dispatcher jobs)"]
        ScraperWorkers["Scraper worker pool\n(per-portal rate-limited)"]
    end

    DB[("PostgreSQL\n(properties, alerts, matches, outbox)")]
    Telegram["Telegram Bot API"]
    Portals["Real-estate portals"]

    Browser -->|HTTPS| API
    API --> DB
    Scheduler --> DB
    Scheduler --> ScraperWorkers
    ScraperWorkers --> Portals
    ScraperWorkers --> DB
    Scheduler --> Telegram
    TelegramApp -.->|receives| Telegram
```

Every box in this diagram already has a named seam in today's architecture: `API` is a new
`presentation/api` package calling the same use-cases the CLI calls today; `Scheduler`/`ScraperWorkers`
are the same `infrastructure/scheduling` + `infrastructure/scrapers` packages running as separate
processes instead of one; `PostgreSQL` is [ADR-003](adr/003-sqlalchemy-as-persistence.md)'s planned
migration, not a new decision.
