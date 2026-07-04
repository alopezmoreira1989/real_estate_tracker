# 008 — Rule Engine via the Specification pattern, Field Registry, and Operator Strategies

> Status: **Accepted** · Date: 2026-07-04

## Context

Driver D1: users must be able to add new alert filters (a new field, a new comparison) without
anyone touching the evaluation engine. The naive approach — a fixed set of DB columns and hand-written
`WHERE`/`if` chains — means every new filter is a schema migration *and* a code change in the one
place everything else depends on.

## Decision

Model conditions as **data**, evaluated by composable `Specification` objects
(`AndSpecification`/`OrSpecification`/`NotSpecification`/`FieldSpecification`), with fields resolved
through a **`FieldRegistry`** of `FieldDescriptor`s (type, accessor, allowed operators) and comparisons
implemented as **Operator Strategies**. A `SpecificationFactory` (ADR-below) turns a persisted
`SearchAlert`'s condition tree into a `Specification` at evaluation time. Full design:
[04-alert-rule-engine.md](../04-alert-rule-engine.md).

## Consequences

- Adding a filter is registering one `FieldDescriptor` — no change to `Specification`, `AlertEngine`,
  or the schema when the field is backed by the `attributes` escape hatch (doc 02 §2).
- Each operator and field is independently unit-testable (table-driven tests per doc 04 §8); the
  engine itself has almost no logic to break.
- The condition tree (`RuleGroup`/`AlertCondition`) is more general than the MVP UI exposes — see
  [ADR-014](014-condition-tree-and-only-mvp-ui.md).

## Alternatives considered

- **Fixed DB columns + hand-written `WHERE`** — rejected: violates D1 directly, every filter is a
  migration.
- **One big `if/elif` inside a single `evaluate()`** — rejected: violates OCP, unbounded growth, high
  risk per edit.

## Revisit when

Not expected to change; this is the structural core the roadmap's Phase 3 exit criteria depend on.
