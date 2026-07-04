# 04 — Alert Engine & Rule Engine

> Status: **Draft for review** · Owner: Architecture · Depends on:
> [02-domain-model.md](02-domain-model.md)

This is the core of the product (driver **D1**): users create unlimited alerts from arbitrary
conditions, and we must be able to add **new filters without changing the engine**. The design uses
the **Specification pattern** with a **field registry** and **operator strategies**.

---

## 1. Two engines, two responsibilities

- **Rule Engine** — *does one property satisfy one alert's conditions?* Pure predicate evaluation.
  No I/O. This is the piece that must stay open for extension, closed for modification.
- **Alert Engine** — *orchestrates* evaluating due alerts against candidate properties, records
  `AlertMatch`es idempotently, and hands new matches to the notification outbox. Uses the Rule
  Engine; adds no filtering logic of its own.

---

## 2. Rule Engine — the Specification pattern

A **`Specification`** answers a single yes/no question about a `Property`:

```python
class Specification(Protocol):
    def is_satisfied_by(self, prop: Property) -> bool: ...
```

Composites let conditions combine without the engine knowing the details:

```python
class AndSpecification(Specification):   # ALL
class OrSpecification(Specification):    # ANY
class NotSpecification(Specification):   # NONE / negate
class FieldSpecification(Specification): # a single leaf: field ⋈ operator ⋈ value
```

A persisted alert's condition tree (`RuleGroup`/`AlertCondition` from doc 02) maps **1:1** onto a
specification tree:

```
RuleGroup(ALL)                     AndSpecification([
├── province == 36          →         FieldSpec(province, EQ, 36),
├── property_type == LAND   →         FieldSpec(property_type, EQ, LAND),
├── price_per_m2 <= 20      →         FieldSpec(price_per_m2, LTE, 20),
├── area >= 3000            →         FieldSpec(area, GTE, 3000),
├── desc contains "water"   →         FieldSpec(description, CONTAINS, "water"),
└── NONE                    →         NotSpecification(OrSpecification([
        └── desc contains "occupied"      FieldSpec(description, CONTAINS, "occupied") ]))
                                    ])
```

Evaluating an alert is just `spec.is_satisfied_by(property)`. Adding OR/NOT logic later is free — the
tree already supports it.

### Why Specification (and what we rejected)

- **Rejected: fixed DB columns + hand-written `WHERE`** — violates D1; every new filter changes the
  schema, the query builder, and the UI. Non-starter.
- **Rejected: a big `if/elif` per field inside one `evaluate()`** — violates OCP; the function grows
  without bound and every filter edit risks the whole engine.
- **Chosen: Specification** — each field/operator is an isolated, unit-testable object; new filters
  are *registration*, not surgery. Composites give boolean logic for free.

---

## 3. Fields as data — the Field Registry

A leaf condition names a **canonical field** (`"price_per_m2"`, `"province"`, `"description"`,
`"features.has_lift"`, `"attributes.energy_rating"`). A **`FieldResolver`** knows, for each field:

- its **type** (`NUMERIC`, `MONEY`, `AREA`, `ENUM`, `TEXT`, `BOOL`, `GEO`),
- how to **extract** its value from a `Property` (an accessor),
- which **operators** are valid for it.

```python
@dataclass(frozen=True)
class FieldDescriptor:
    key: str
    type: FieldType
    extract: Callable[[Property], Any]
    allowed_operators: frozenset[Operator]

class FieldRegistry:
    def register(self, descriptor: FieldDescriptor) -> None: ...
    def get(self, key: str) -> FieldDescriptor: ...
```

**Adding a new filter = registering one `FieldDescriptor`.** No engine code changes. This is the
mechanism that satisfies D1 concretely. Fields backed by the `attributes` escape hatch (doc 02) are
registered the same way, pointing their accessor at `attributes[key]`.

---

## 4. Operators as strategies

Each `Operator` is a small **Strategy** — a pure comparison, chosen by the field's type:

| Operator | Applies to | Semantics |
|----------|-----------|-----------|
| `EQ`, `NEQ` | all | equality (enums compared by canonical value) |
| `LT`,`LTE`,`GT`,`GTE` | NUMERIC/MONEY/AREA | ordered comparison (unit-safe via VOs) |
| `BETWEEN` | NUMERIC/MONEY/AREA | inclusive range |
| `IN`,`NOT_IN` | ENUM/NUMERIC/TEXT | membership |
| `CONTAINS`,`NOT_CONTAINS` | TEXT | case/accent-insensitive substring/token match |
| `EXISTS`,`NOT_EXISTS` | all | value present / absent (handles tri-state, doc 02) |
| `WITHIN_RADIUS` | GEO | distance ≤ r from a point (future) |

`FieldSpecification` composes a **field accessor** (from the registry) with an **operator strategy**:

```python
class FieldSpecification(Specification):
    def is_satisfied_by(self, prop: Property) -> bool:
        actual = self.descriptor.extract(prop)     # unit-typed VO or scalar
        return self.operator_strategy.compare(actual, self.expected)
```

Validity is enforced at **construction** (doc 02 invariant): building a `CONTAINS` on a `NUMERIC`
field raises immediately — a bad alert can never reach evaluation.

### Text matching (the "water"/"occupied" case)

`CONTAINS`/`NOT_CONTAINS` normalize both sides: lowercase, strip accents (`agua` vs `água`), and
match on word/substring per configuration. This is where Spanish diacritics are handled once, in one
strategy, rather than sprinkled through the code.

---

## 5. Building specs from persisted alerts — the Factory

The domain never reads rows directly. A **`SpecificationFactory`** turns a `SearchAlert`'s condition
tree into a `Specification`:

```python
class SpecificationFactory:
    def __init__(self, fields: FieldRegistry, operators: OperatorRegistry): ...
    def build(self, alert: SearchAlert) -> Specification:
        return self._node(alert.conditions)     # recurse RuleGroup/AlertCondition
```

It recurses the tree, resolves each field via the registry, selects the operator strategy, and
assembles composites. Unknown field/operator ⇒ a typed `InvalidConditionError` (should already be
impossible thanks to construction-time validation, but defended here for data loaded from an older
schema).

---

## 6. Alert Engine — orchestration

```python
class AlertEngine:
    def evaluate(self, alert: SearchAlert, candidates: Iterable[Property]) -> list[AlertMatch]:
        spec = self.factory.build(alert)
        new_matches = []
        for prop in candidates:
            if spec.is_satisfied_by(prop):
                match = AlertMatch.new(alert.id, prop.id)   # value object w/ natural key
                new_matches.append(match)
        return new_matches
```

Idempotency (doc 03): persisting matches uses the UNIQUE `(alert_id, property_id)` constraint — an
already-known match is a no-op, so re-evaluating the same candidates never re-notifies. The engine
returns *candidate* matches; the repository/UoW decides which are genuinely new and enqueues
notifications only for those.

**Candidate selection** is not "every property ever". The Search Engine (doc 06) narrows candidates
using the alert's *portal-pushable* conditions (province, price range, type) so the Rule Engine only
evaluates a small, relevant set client-side.

---

## 7. Extensibility walk-through (adding "energy rating ≥ B")

1. Ensure the Normalizer populates `attributes["energy_rating"]` (or promote to a column).
2. Register a `FieldDescriptor(key="energy_rating", type=ENUM, extract=..., allowed_operators={EQ, IN, GTE})`.
3. Done. Users can now build the condition; persistence, factory, engine, and evaluation already work.

No change to `Specification`, `AlertEngine`, the DB schema (if using `attributes`), or the API shape.
That is the proof that D1 is satisfied.

---

## 8. Testing strategy for the engine

- **Operator strategies**: table-driven unit tests (each operator × representative values, incl.
  `None`/tri-state edges).
- **FieldSpecification**: extraction + operator per field type.
- **Composites**: truth-table tests for AND/OR/NOT nesting.
- **Factory**: round-trip persisted tree → spec → evaluation.
- **Property-based tests** (Hypothesis): "a NOT(spec) is satisfied iff spec is not" and similar
  algebraic laws.
- **Golden alert fixtures**: the "Urbanizable land in Pontevedra" example as an end-to-end fixture.

---

## 9. Open questions for review

1. MVP condition logic: expose **AND-only** in the UI while modeling the full tree? (Proposed: yes.)
2. Where do keyword `CONTAINS` filters run — Python engine (proposed for MVP) or pushed to DB FTS?
3. Do we allow **cross-field** conditions (e.g. `price_per_m2` derived at query time) as first-class,
   or only pre-computed fields? (Proposed: derived fields computed on the `Property` and registered
   like any other field.)
