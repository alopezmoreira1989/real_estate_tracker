# 002 — Domain-Driven Design, deliberately "lite"

> Status: **Accepted** · Date: 2026-07-04

## Context

The domain has real modeling problems worth solving carefully: a canonical `Property` that must mean
the same thing regardless of source portal, an alert whose conditions form a tree with invariants
that must never be violated, and a vocabulary (property types, land types, provinces) that must be
controlled rather than free text. Classic DDD (Evans/Vernon) gives vocabulary for exactly this —
entities, value objects, aggregates, a ubiquitous language. But full DDD also brings bounded contexts
with anti-corruption layers between them, domain events with an event bus, CQRS, and sometimes event
sourcing — machinery aimed at large systems with multiple teams and subdomains in tension with each
other.

## Decision

Adopt DDD's **modeling vocabulary and discipline**, not its **distributed-systems machinery**:

- **Entities** (`Property`, `SearchAlert`, `AlertMatch`, `User`) have identity and a lifecycle.
- **Value objects** (`Money`, `Area`, `Location`, `Features`, …) are immutable, compared by value, and
  carry their own validation so an invalid `Money` or out-of-range `GeoPoint` cannot exist.
- **`SearchAlert` is an aggregate root** — its `AlertCondition`/`RuleGroup` tree is only ever modified
  through the root, which is what makes "an alert always has ≥1 valid condition" an invariant instead
  of a hope.
- A single **ubiquitous language** (`Property`, `Listing`, `Alert`, `Rule`, `Match`, `Normalizer`) is
  used identically in code, docs, commit messages, and UI copy — see
  [02-domain-model.md](../02-domain-model.md) §1.

Explicitly **not** adopted for this phase: multiple bounded contexts (there is one domain, not several
in tension), domain events / event sourcing (nothing yet needs an audit log of state transitions
beyond `PriceHistory`, which is a plain append-only table), and CQRS (read and write models are the
same `Property`/`SearchAlert` shapes — there is no query-side complexity that would justify
splitting them).

## Consequences

- The domain stays small and readable: one aggregate (`SearchAlert`), a handful of entities, and VOs
  — a newcomer can hold the whole model in their head.
- Invariants (condition validity, tri-state features, unit-safe VOs) are enforced at construction,
  not by hoping every caller remembers to validate — this is the concrete payoff of "aggregate" over
  "just a Pydantic model with public fields."
- If the system later needs genuine event-driven fan-out (e.g. many independent consumers reacting to
  a new match) or a second subdomain with its own language, this ADR should be revisited rather than
  silently growing machinery in place — see *Revisit when*.

## Alternatives considered

- **Full DDD with bounded contexts and an internal event bus** — over-engineered for a single-domain,
  single-team project; the coordination overhead (anti-corruption layers, published-language
  contracts between contexts) has no problem to solve yet. Rejected as premature (YAGNI, CLAUDE.md
  §5).
- **Anemic domain model** (plain dataclasses with no behavior; validation lives in the application
  layer or DTOs) — the classic anti-pattern DDD warns about. It would let `AlertCondition` trees exist
  in invalid states between validation calls, and duplicates validation logic wherever an alert is
  constructed (CLI, future API, tests). Rejected.
- **Event sourcing for `Property`/`SearchAlert`** — would give a full history of every change "for
  free," but adds a projection/replay machinery cost that isn't earned yet; `PriceHistory` already
  captures the one history that matters (price over time) as a simple append-only table. Rejected for
  now.

## Revisit when

A second genuinely distinct subdomain appears (e.g. billing/subscriptions for multi-tenant SaaS, V3),
or multiple independent consumers need to react to domain state changes asynchronously — at that
point domain events and/or bounded contexts earn their keep.
