# Phase 3 Plan — Rule Engine (Issues #12–#17)

> Status: **Awaiting approval** · Branch: `dev_alm` · Depends on: Phase 2 (merged)
> Design reference: [../architecture/04-alert-rule-engine.md](../architecture/04-alert-rule-engine.md)

## Goal

Turn a `SearchAlert`'s condition tree (built in Phase 2) into an executable
`Specification` that answers *"does this `Property` match?"*, using the
**Specification + Field Registry + Operator Strategy** design. All code is pure
domain — no framework imports (import-linter enforced).

## New modules

```
src/real_estate/domain/rules/
├── specification.py   # Specification protocol + And/Or/Not composites + FieldSpecification
├── operators.py       # OperatorStrategy per Operator, accent/case folding, lookup table
├── field_registry.py  # FieldType, FieldDescriptor, FieldRegistry, default_registry()
├── factory.py         # SpecificationFactory: condition tree → Specification
└── __init__.py
src/real_estate/domain/services/
└── alert_engine.py    # AlertEngine.evaluate(alert, candidates) → list[AlertMatch]
src/real_estate/domain/model/
└── match.py           # AlertMatch entity (exported from model/__init__)
```

## Issue-by-issue scope

### #12 — Specification + composites
- `Specification` protocol: `is_satisfied_by(prop: Property) -> bool`.
- `AndSpecification`, `OrSpecification`, `NotSpecification`
  (`GroupOperator.ALL → And`, `ANY → Or`, `NONE → Not(Or(children))`).
- `FieldSpecification` leaf holding a `FieldDescriptor`, an `OperatorStrategy`,
  and the expected value.

### #14 — Operator strategies
- `OperatorStrategy` protocol `compare(actual, expected) -> bool`; one
  implementation per `Operator`: EQ, NEQ, LT, LTE, GT, GTE, BETWEEN, IN, NOT_IN,
  CONTAINS, NOT_CONTAINS, EXISTS, NOT_EXISTS.
- `CONTAINS`/`NOT_CONTAINS` fold **case and Spanish accents** once (`agua` ≡ `água`).
- Tri-state rule: `None` (unknown) fails positive scalar comparisons; only
  `EXISTS`/`NOT_EXISTS` inspect presence.
- `OPERATORS: dict[Operator, OperatorStrategy]` lookup.

### #13 — Field Registry
- `FieldType` enum (NUMERIC, MONEY, AREA, ENUM, TEXT, BOOL, GEO);
  `FieldDescriptor(key, type, extract, allowed_operators)`; `FieldRegistry`.
- `default_registry()` registers MVP fields: `province`, `municipality`,
  `property_type`, `land_type`, `listing_type`, `status`, `price`,
  `price_per_m2`, `area`, `plot_area`, `rooms`, `bathrooms`, `postal_code`,
  `title`, `description`, `features.has_lift|has_terrace|has_garden|has_parking|has_pool|is_new_build`.
- **Key decision — compare via primitives:** each `extract` returns a plain
  comparable (`"36"`, `"LAND"`, `Decimal`, `int`, `bool`, `None`) matching the
  scalar representation stored in the condition tree, so operators stay trivial
  and no value-object/scalar mismatch occurs.

### #15 — SpecificationFactory
- `build(alert) -> Specification`, recursing the tree (leaf → `FieldSpecification`,
  group → composite).
- Raises `InvalidConditionError` for an unknown field or an operator not allowed
  for the field's type (defends against stale persisted data).

### #16 — AlertEngine + AlertMatch
- Add `AlertMatch` domain entity: natural key `(alert_id, property_id)`,
  `matched_at`, `status`; equality by natural key (basis for idempotency).
- `AlertEngine.evaluate(alert, candidates, *, now) -> list[AlertMatch]` — pure,
  deterministic (clock injected).
- **Scope note:** the engine is pure and returns candidate matches. *Persisted*
  idempotency (the existing `UNIQUE(alert_id, property_id)` + a `MatchRepository`)
  is wired in the `RunAlertCycle` use-case in **Phase 5 (#28)**, keeping the
  domain framework-free.

### #17 — Tests + golden fixture
- Table-driven operator tests (incl. `None`/tri-state edges, accent folding).
- `FieldSpecification` + composite truth-table tests; factory round-trip
  (tree → spec → eval).
- **Golden fixture** — the "Urbanizable land in Pontevedra" alert
  (province=36, type=LAND, land=URBANIZABLE, price/m²≤20, area≥3000,
  description contains "water", NOT contains "occupied") evaluated over a small
  `Property` set, asserting exact matches/misses.
- **Hypothesis** property tests for algebraic laws (`NOT(NOT s) ≡ s`, De Morgan,
  AND/OR identity). Adds `hypothesis` to the `dev` extra in `pyproject.toml`.

## Cross-cutting
- New dependency: `hypothesis` (dev only). No runtime deps added.
- No schema/migration changes. Domain purity preserved (import-linter 4/4).

## Process (same cadence as Phase 2)
- Work on `dev_alm`, in dependency order **#12 → #14 → #13 → #15 → #16 → #17**,
  one commit per issue.
- Full gate green on every commit: `ruff`, `black`, `mypy --strict`,
  `lint-imports`, `pytest`.
- Push per issue (CI runs); at the end open a PR `dev_alm → main` and pause for
  approval to merge (issues #12–#17 close on merge).

## Out of scope (deferred by design)
- Match persistence / `MatchRepository` and idempotent writes → Phase 5 (#27–#28).
- Keyword filters pushed to DB FTS → V2 (ADR-012); MVP evaluates in Python.
- `WITHIN_RADIUS` / geo operators → V3.
