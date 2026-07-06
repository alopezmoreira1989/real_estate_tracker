# 10 — Future-Proofing & Architectural Risks

> Status: **Accepted** · Owner: Architecture · Depends on: [01-architecture.md](01-architecture.md),
> [09-diagrams.md](09-diagrams.md)

Written during **Phase 1.5** (repository hardening, before any domain code exists) to pressure-test
the Phase 1 skeleton against the extensions the roadmap already commits to: more portals, more
notification channels, a REST API, a web UI, authentication, and multi-user support. For each, this
doc states **where the seam already is**, what (if anything) is genuinely at risk, and — per the
Phase 1.5 scope — documents the risk rather than building against it early.

---

## 1. Adding a new real-estate portal

**Seam:** `infrastructure/scrapers/<portal>/` + `infrastructure/normalizers/<portal>/`, registered
into `ScraperRegistry`/`NormalizerRegistry` (doc 05 §4), plus one row of `portal.capabilities` (doc 03).

**Already handled by the current design:**
- [ADR-009](adr/009-canonical-property-normalizer-confinement.md) confines all portal-specific
  knowledge to that portal's Normalizer; the Rule Engine, persistence, and notifications never change.
- [ADR-004](adr/004-playwright-for-scraping.md) lets each portal choose its own fetch strategy
  independently.
- Adding a portal is additive per doc 07 ("co-located per portal").

**Risk:** none structural. The practical cost is real but expected: a new mapping table + fixtures per
portal (doc 05 §7), and tuning that portal's rate limits/circuit breaker (doc 06 §5). Cross-portal
duplicate listings are an accepted, deferred UX gap ([ADR-013](adr/013-defer-cross-portal-dedup.md))
until a second portal actually ships.

---

## 2. Adding a new notification provider

**Seam:** a new `Notifier` port implementation in `infrastructure/notifications/`, plus a
`channel_type` value on `NotificationChannel` (doc 03).

**Already handled:** [ADR-012](adr/012-notification-outbox.md)'s outbox decouples detection from
delivery — a new channel is purely additive, no change to matching or the dispatcher's core loop.
[ADR-005](adr/005-telegram-notifications.md) documents Telegram as *a* choice, not *the* architecture.

**Risk:** per-user multi-channel fan-out (send the same match to two channels a user configured) isn't
designed yet — the schema allows multiple `NotificationChannel` rows per user, but the dispatcher
today assumes "the channel," not "channels." Flagged in ADR-005's *Revisit when*; a real design task
for whichever of V2/V3 first needs it, not a blocker today.

---

## 3. Adding a REST API (FastAPI, V2)

**Seam:** `presentation/api/` calling the same `application/use_cases/` the CLI calls (doc 07,
[09-diagrams.md](09-diagrams.md) §2).

**Already handled:** presentation is explicitly thin and use-case-driven per
[ADR-001](adr/001-clean-architecture.md); nothing in `application`/`domain` assumes a CLI-shaped
caller. DTOs at the application boundary (Pydantic, doc 07) are already the same shape a FastAPI
request/response model would validate against.

**Risk:** **request-scoped concurrency.** The CLI/scheduler today is single-process, effectively
single-writer against SQLite. A FastAPI surface serving concurrent HTTP requests against the same
database needs the PostgreSQL migration ([ADR-003](adr/003-sqlalchemy-as-persistence.md)) in place
*first*, or SQLite's single-writer behavior will surface as request latency/lock contention. This is
already sequenced correctly in the roadmap (FastAPI and PostgreSQL are both V2), but is worth stating
explicitly: **do not ship the API before the PostgreSQL migration** unless traffic is trivial enough
that SQLite's write serialization is a non-issue.

---

## 4. Adding a Web UI (Streamlit now, richer web UI later)

**Seam:** `presentation/web/` calling `application/use_cases/`, per Phase 8 of the roadmap.

**Already handled:** Streamlit is explicitly a *dev-facing verification surface* (roadmap Phase 8,
CLAUDE.md §9), not a production UI — it runs against the same use-cases and is exercised on `dev_alm`
before every merge to `main`. A richer end-user web UI (V3, alongside the REST API) would be a second,
independent `presentation` package calling the same use-cases; it does not replace or couple to
Streamlit.

**Risk:** none structural for the dashboard as scoped. If a production, multi-user web UI is built
directly against the domain instead of through the API (bypassing `presentation/api/`), that would
create two divergent presentation paths with duplicated request/response mapping — the guardrail is
simply to route every future UI through the same use-cases (and, once it exists, the same API), never
around them.

---

## 5. Adding authentication

**Seam:** none yet — this is the one area Phase 1 has **not** built a port for, because the MVP is
single-user with no login (CLAUDE.md §1).

**Risk (real, not yet mitigated):** `User` already exists as an entity and every user-owned row
already carries `user_id` ([ADR](adr/) — see driver D5, doc 01 §9), so *authorization* (scoping
queries by user) is structurally ready. **Authentication** (proving who the caller is) is not: there
is no `AuthProvider`/session port, and `presentation/api` doesn't exist yet to need one. When the
REST API ships (V2) or multi-user sign-up ships (V3), authentication must be designed as a new port
(e.g. a `Principal`/`AuthContext` passed into use-cases) rather than checked ad hoc inside route
handlers — otherwise authorization checks risk being duplicated or forgotten per-endpoint. Recorded
here as a known gap to design deliberately, not a silent risk.

---

## 6. Docker deployment

**Seam:** already built (Phase 1, issue #5) — multi-stage `Dockerfile`, non-root user,
`docker-compose.yml` with an `app` service and a Postgres service defined ahead of need.

**Risk:** none for the MVP. The compose file's Postgres service is unused today
([ADR-003](adr/003-sqlalchemy-as-persistence.md)) — the risk to watch is letting compose config drift
out of sync with the actual connection settings once the PostgreSQL migration lands; the migration's
own PR should update `docker-compose.yml` env vars in the same change, not as an afterthought.

---

## 7. Cloud deployment

**Seam:** none built yet — intentionally, per Phase 1.5 scope (structure only, no premature
infrastructure).

**Risk:** the scheduler design (doc 06 §5 — a single planner job, per-portal worker pools, in-process
circuit breakers) assumes **one running instance**. Horizontally scaling the scheduler across multiple
cloud instances without coordination would double-scrape (multiple planners picking up the same due
alerts) or double-dispatch notifications. This is explicitly a **non-goal for the MVP**
(doc 01 §2: "horizontal scaling" is listed as out of scope), but is flagged here so a future cloud
deployment adds a coordination mechanism (a leader-election lock, or a single scheduler
replica with horizontally-scaled stateless workers behind it) rather than naively running N copies of
today's scheduler.

---

## 8. Multiple users (V3)

**Seam:** driver D5 (doc 01 §9) — every user-owned entity already carries `user_id`; no module holds
"the current user" as global/singleton state; `SearchCache`/`Property` are deliberately global and
shared *across* users (this is what makes dedup, [ADR-011](adr/011-search-dedup-by-canonical-signature.md),
work across tenants for free).

**Risk:** **fairness/quota enforcement doesn't exist yet.** Doc 06 §6 already names this ("a per-user
quota is a config knob, off for the single-user MVP, ready for later") but it is not implemented —
today, nothing stops one user's alerts from dominating the due-set or the per-portal concurrency
budget once a second user exists. This is correctly scoped as V3 work, not a Phase 1.5 fix, but is the
single biggest gap between "multi-tenant by design" (schema-level) and "multi-tenant in practice"
(fair resource allocation) — call it out explicitly when V3 planning starts.

---

## Summary table

| Extension | Structural seam ready? | Real risk to design deliberately (not yet mitigated) |
|-----------|:---:|--------|
| New portal | ✅ | None structural |
| New notification channel | ✅ | Per-user multi-channel fan-out |
| REST API | ✅ | Must follow the PostgreSQL migration, not precede it |
| Web UI | ✅ | Keep future UIs routed through use-cases/API, never around them |
| Authentication | ⚠️ partial (authorization yes, authentication no) | Design an explicit auth port before the API ships |
| Docker deployment | ✅ (built) | Keep compose config in sync with the PostgreSQL migration |
| Cloud deployment | ⚠️ | Scheduler assumes a single instance; needs coordination before scaling out |
| Multi-user | ⚠️ partial (schema yes, fairness no) | Per-user quota/fairness enforcement is unimplemented |
