# 08 — Sequence Diagrams

> Status: **Accepted** · Owner: Architecture · Depends on:
> [06-search-scheduler.md](06-search-scheduler.md)

Runtime behavior of the key flows. Actors are grouped by layer (doc 01): **P**resentation,
**A**pplication, **D**omain, **I**nfrastructure.

---

## 1. Create an alert

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI (P)
    participant UC as CreateAlert (A)
    participant Dom as SearchAlert aggregate (D)
    participant Reg as FieldRegistry (D)
    participant Repo as AlertRepository (I)
    participant UoW as UnitOfWork (I)

    User->>CLI: create-alert "Land Pontevedra" --cond ...
    CLI->>UC: CreateAlertRequest (DTO)
    UC->>Reg: validate each field+operator
    Reg-->>UC: OK / InvalidConditionError
    UC->>Dom: SearchAlert.create(user, name, conditions)
    Dom-->>UC: alert (invariants enforced)
    UC->>UoW: begin
    UC->>Repo: add(alert)
    UC->>UoW: commit
    UoW-->>UC: ok
    UC-->>CLI: AlertCreated(id)
```

Field/operator validity is checked **before** persistence; a malformed alert never reaches the DB.

---

## 2. Alert cycle — the core flow (dedup + evaluate + enqueue)

```mermaid
sequenceDiagram
    participant Sched as Planner job (I)
    participant UC as RunAlertCycle (A)
    participant Plan as SearchPlanner (A)
    participant Cache as SearchCache (I)
    participant Scr as Scraper (I)
    participant Norm as Normalizer (I)
    participant PRepo as PropertyRepository (I)
    participant Eng as AlertEngine (D)
    participant Out as Notification outbox (I)

    Sched->>UC: run(due_alerts)
    UC->>Plan: plan(due_alerts)
    Plan->>Plan: split pushable / client-side
    Plan->>Plan: build PortalQuery + canonical signature
    Plan-->>UC: groups{ signature -> [alerts], portalQuery }

    loop for each unique signature
        UC->>Cache: get(signature)
        alt cache fresh
            Cache-->>UC: cached property ids
        else miss / stale
            UC->>Scr: fetch(portalQuery)
            Scr-->>UC: [RawListing]  (record SearchExecution)
            loop each RawListing
                UC->>Norm: normalize(raw)
                Norm-->>UC: Property (+issues)
                UC->>PRepo: upsert(property)  (+ PriceHistory if changed)
            end
            UC->>Cache: put(signature, property ids, ttl)
        end

        loop each alert on this signature
            UC->>Eng: evaluate(alert, candidate properties)
            Eng-->>UC: [candidate AlertMatch]
            UC->>PRepo: persist new matches (UNIQUE alert,property)
            UC->>Out: enqueue notifications for genuinely-new matches
        end
        UC->>UC: set last_run_at for alerts
    end
```

Note the two dedup wins: **one scrape per signature** (D3) and **idempotent matches** (UNIQUE
constraint) so re-runs never double-notify.

---

## 3. Notification dispatch (separate job)

```mermaid
sequenceDiagram
    participant Disp as Dispatcher job (I)
    participant NRepo as NotificationRepository (I)
    participant Ch as NotificationChannel (D)
    participant Tg as TelegramNotifier (I)

    Disp->>NRepo: fetch PENDING (respect frequency)
    NRepo-->>Disp: [Notification]
    loop each notification
        Disp->>Ch: resolve channel + rate limit
        Disp->>Tg: send(message)
        alt success
            Tg-->>Disp: ok
            Disp->>NRepo: mark SENT (sent_at)
        else failure
            Tg-->>Disp: error
            Disp->>NRepo: attempts++, last_error, keep PENDING or FAILED after N
        end
    end
```

Delivery lives entirely in infrastructure; the domain only produced `AlertMatch`. Adding Email/
Discord later is a new `Notifier` adapter + channel type — no change to detection or dispatch loop.

---

## 4. Scraper failure isolation

```mermaid
sequenceDiagram
    participant UC as RunAlertCycle (A)
    participant Scr as FotocasaScraper (I)
    participant CB as CircuitBreaker (I)
    participant Log as structlog (I)

    UC->>CB: allow(fotocasa)?
    alt breaker open
        CB-->>UC: blocked
        UC->>Log: warn portal paused; skip signature
    else allowed
        UC->>Scr: fetch(query)  [tenacity retry+backoff]
        alt success
            Scr-->>UC: [RawListing]
            UC->>CB: record success
        else repeated failure
            Scr-->>UC: error
            UC->>CB: record failure (maybe open breaker)
            UC->>Log: error SearchExecution=FAILED
            Note over UC: cycle continues with other portals (D7)
        end
    end
```

One portal breaking never halts the cycle; other signatures/portals proceed.
