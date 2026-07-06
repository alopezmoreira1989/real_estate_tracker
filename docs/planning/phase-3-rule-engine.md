# Phase 3 Plan — Rule Engine (Issues #12–#17)

> Status: **Implemented on `dev_alm` — PR to `main` pending approval** · Depends on: Phase 2 (merged)
> Design reference: [../architecture/04-alert-rule-engine.md](../architecture/04-alert-rule-engine.md)
> Handoff / current state: see the last section of this doc.

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

---

## Handoff — state as of 2026-07-05 (stopped mid-phase by request)

### Done (all committed + pushed to `dev_alm`, CI/gate green)
All Phase 3 **code is complete**. Full gate green locally: ruff, black,
mypy --strict (60 files), import-linter (4/4, domain still framework-free),
**108 tests passing**, ~93% coverage.

| Issue | Commit | What landed |
|-------|--------|-------------|
| #14 | operator strategies | `domain/rules/operators.py` — `OperatorStrategy` + all operators, accent/case folding, tri-state None, `strategy_for()` |
| #13 | field registry | `domain/rules/field_registry.py` — `FieldType`, `FieldDescriptor`, `FieldRegistry`, `default_registry()` |
| #12 | specification | `domain/rules/specification.py` — `Specification` + And/Or/Not + `FieldSpecification` |
| #15 | factory | `domain/rules/factory.py` — `SpecificationFactory.build(alert)`; `domain/rules/__init__.py` exports |
| #16 | engine | `domain/model/match.py` (`AlertMatch`, `MatchStatus`), `domain/services/alert_engine.py` (`AlertEngine`) |
| #17 | tests | golden "Urbanizable land in Pontevedra" fixture + Hypothesis laws; `hypothesis` added to dev deps |

GitHub issues #12–#17 remain **OPEN** (they auto-close when `dev_alm` merges to
`main`).

### Left to do (the only remaining Phase 3 step)
1. **Open PR `dev_alm → main`** for Phase 3 and merge after CI is green — this
   was intentionally paused for user approval. `dev_alm` is ahead of `main` by
   the Phase 3 commits. On merge, issues #12–#17 close.
   - Suggested PR title: `Phase 3: Rule Engine (#12–#17)`.
   - Body should `Closes #12 … #17`.

### Resume checklist for next session
- `source .venv/Scripts/activate`; gate: `pre-commit run --all-files` (or run
  ruff/black/mypy/lint-imports/pytest individually).
- Then start **Phase 4 — Normalization** (#18 `RawListing`/`NormalizationResult`
  → #22 golden fixtures). The `Normalizer` port and `RawListing` DTO already
  exist from Phase 2 (`domain/ports/`); the field registry + vocabularies from
  Phases 2–3 are the normalization targets.
- Reminder: `AlertEngine` is pure and returns candidate `AlertMatch`es;
  persistence/idempotency wiring is Phase 5 (#28).
