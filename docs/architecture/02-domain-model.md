# 02 — Canonical Domain Model

> Status: **Draft for review** · Owner: Architecture · Depends on: [01-architecture.md](01-architecture.md)

The domain model is the shared language of the whole system. Everything after normalization speaks
**only** in these terms. This document defines the entities, value objects, and controlled
vocabularies that make up the canonical model.

---

## 1. Building blocks

We distinguish:

- **Entities** — have identity and a lifecycle (`Property`, `SearchAlert`, `AlertMatch`, `User`).
- **Value Objects (VO)** — immutable, compared by value, no identity (`Money`, `Area`, `GeoPoint`,
  `Location`, `PricePerM2`). VOs carry units and validation so the rest of the code cannot get them
  wrong.
- **Aggregates** — a consistency boundary with a root entity. `SearchAlert` is an aggregate root
  owning its `AlertCondition`s; you never modify a condition except through its alert.

Domain objects are **framework-free** (see D-rule in doc 01). We use `@dataclass(frozen=True)` for
VOs and plain classes/dataclasses for entities.

---

## 2. The canonical `Property`

`Property` is the universal, portal-independent representation of a listing.

```python
@dataclass
class Property:
    id: PropertyId                     # our identity (surrogate)
    listing_type: ListingType          # SALE | RENT | AUCTION | TRANSFER
    property_type: PropertyType         # FLAT | HOUSE | LAND | GARAGE | ...
    land_type: LandType | None          # only when property_type == LAND
    location: Location                  # VO: province/municipality/... + geo
    price: Money | None                 # VO: amount + currency
    area: Area | None                   # VO: built area in m²
    plot_area: Area | None              # VO: land/plot area in m² (for LAND/HOUSE)
    rooms: int | None
    bathrooms: int | None
    features: Features                  # VO: normalized common booleans
    attributes: Mapping[str, str]       # normalized-but-uncommon key/values (escape hatch)
    title: str
    description: str
    media: Media                        # image/video urls (VO)
    published_at: datetime | None
    status: ListingStatus               # ACTIVE | INACTIVE | UNKNOWN

    # --- derived (computed, never stored as source of truth) ---
    @property
    def price_per_m2(self) -> PricePerM2 | None: ...
```

Notes:

- **Derived fields** (`price_per_m2`) are computed from VOs, so units are guaranteed consistent.
  They are still *persisted* (denormalized) for indexed querying — see DB doc — but the domain owns
  the calculation.
- **`attributes`** is a deliberate, controlled escape hatch: normalized *values* keyed by a small,
  documented set of canonical keys, for fields too rare to promote to first-class columns. The rule
  engine can target them, but promotion to a real field is preferred when a filter becomes common.
- A `Property` is **canonical/deduped**. The raw, per-portal source lives in `PortalListing`
  (see DB doc); a `Property` may be backed by several `PortalListing`s.

### Value objects

| VO | Fields | Invariants |
|----|--------|-----------|
| `Money` | `amount: Decimal`, `currency: Currency=EUR` | amount ≥ 0; arithmetic only within same currency |
| `Area` | `value: Decimal`, `unit=M2` | value > 0 |
| `PricePerM2` | `value: Decimal` | derived; value > 0 |
| `Location` | `country`, `province`, `municipality`, `district?`, `postal_code?`, `geo?` | province ∈ controlled `Province`; municipality validated against province |
| `GeoPoint` | `lat`, `lng` | valid ranges |
| `Features` | booleans: `has_lift`, `has_terrace`, `has_garden`, `has_parking`, `has_pool`, `is_new_build`, … | tri-state via `bool | None` (unknown ≠ false) |
| `Media` | `images: tuple[str,...]`, `videos: tuple[str,...]` | urls validated |

> **Tri-state booleans**: absence of information (portal didn't say) must be distinguishable from an
> explicit "no". `Features` uses `bool | None`; the rule engine treats `None` as "does not match"
> for positive conditions unless the operator is `EXISTS`.

---

## 3. Controlled vocabularies (enums)

Controlled values replace portal-specific free text. Each has a **mapping table** owned by the
Normalizer layer (see [05-normalization.md](05-normalization.md)).

- **`ListingType`**: `SALE`, `RENT`, `AUCTION`, `TRANSFER`.
- **`PropertyType`**: `FLAT`, `PENTHOUSE`, `DUPLEX`, `STUDIO`, `HOUSE`, `CHALET`, `LAND`, `GARAGE`,
  `STORAGE_ROOM`, `OFFICE`, `COMMERCIAL`, `BUILDING`, `OTHER`.
- **`LandType`** (only when `PropertyType == LAND`): `URBAN`, `URBANIZABLE`, `RUSTIC`,
  `NON_DEVELOPABLE`, `UNKNOWN`.
- **`Province`**: the 52 Spanish provinces, keyed by **INE code** (e.g. `36 = Pontevedra`). Using the
  official code as the canonical key makes municipality validation and future data joins reliable.
- **`Municipality`**: keyed by INE municipality code; belongs to exactly one `Province`.
- **`Currency`**: `EUR` (extensible).
- **`ListingStatus`**: `ACTIVE`, `INACTIVE`, `UNKNOWN`.

> **Why INE codes?** They are stable, official, and unambiguous across portals that spell names
> differently ("A Coruña" / "La Coruña" / "Coruña"). The Normalizer maps portal text → INE code.

The `OTHER`/`UNKNOWN` members are intentional: normalization must **never silently drop** a listing
it can't classify — it maps to `OTHER`/`UNKNOWN` and flags it for review, so we discover missing
mappings instead of losing data.

---

## 4. The Alert aggregate

```
SearchAlert (aggregate root)
├── id, user_id, name
├── portals: set[PortalId]           # which portals this alert monitors
├── frequency: Frequency             # e.g. every 15 min
├── is_active: bool
├── created_at, updated_at
└── conditions: RuleGroup            # root of the condition tree (see doc 04)
        └── children: [AlertCondition | RuleGroup ...]
```

- **`AlertCondition`** — a single predicate: `field` (canonical), `operator`, `value(s)`.
- **`RuleGroup`** — a boolean combinator (`ALL`/`AND`, `ANY`/`OR`, `NONE`/`NOT`) over children,
  enabling arbitrarily nested logic. MVP UI exposes a single top-level `ALL` group (AND-only), but
  the model supports the full tree so nothing changes structurally later.

Invariants enforced by the aggregate:

- A condition's `field` must be a registered canonical field; its `operator` must be valid for that
  field's type (a `CONTAINS` on a numeric field is rejected at construction).
- An alert always has at least one condition.
- Editing conditions goes through the `SearchAlert` root (keeps the tree valid + bumps `updated_at`).

Full engine design: [04-alert-rule-engine.md](04-alert-rule-engine.md).

---

## 5. Supporting entities

| Entity | Purpose | Key relationships |
|--------|---------|-------------------|
| `User` | Owner of alerts & channels | 1—N `SearchAlert`, 1—N `NotificationChannel` |
| `Portal` | A monitored website (config, base URL, capabilities) | referenced by `PortalListing`, `SearchExecution` |
| `PortalListing` | Raw-source record of one listing on one portal | N—1 `Property`, N—1 `Portal` |
| `Property` | Canonical listing | 1—N `PriceHistory`, 1—N `PortalListing`, N—M `SearchAlert` via `AlertMatch` |
| `PriceHistory` | Time series of a property's price | N—1 `Property` |
| `AlertMatch` | Fact: property satisfied an alert | N—1 `SearchAlert`, N—1 `Property` |
| `Notification` | Outbox message for a match | N—1 `AlertMatch`, N—1 `NotificationChannel` |
| `NotificationChannel` | A user's configured delivery target (Telegram chat, email, …) | N—1 `User` |
| `SearchExecution` | A single scrape run of one portal query | N—1 `Portal` |
| `SearchCache` | Cached result set keyed by query signature | referenced by dedup logic |

Detailed columns, keys, indexes and constraints: [03-database.md](03-database.md).

---

## 6. Identity & equality

- Entities use **surrogate ids** (`PropertyId`, `AlertId`, …) as typed wrappers (NewType/`UUID`),
  not raw ints scattered around, so signatures are self-documenting and mixing ids is a type error.
- `PortalListing` additionally has a **natural key** `(portal_id, external_id)` — the portal's own
  listing id — used for upsert and dedup.
- `Property` canonical identity comes from a **fingerprint** (see DB doc §Dedup) when we merge
  cross-portal duplicates; if dedup is deferred, `Property` ↔ `PortalListing` is simply 1—1.

---

## 7. Why a canonical model at all (design rationale)

Without it, portal quirks (`precio` vs `price` vs `importe`, m² as `"120 m²"` vs `120.0`, "La
Coruña" vs INE `15`) leak into the rule engine, the DB schema, notifications, and the UI — every new
portal would ripple through the entire codebase (violating OCP/DRY). The canonical model confines
all portal knowledge to a single, testable seam (the Normalizer), and lets the engine, storage, and
notifications be written **once**.

---

## 8. Open questions for review

1. Do we promote `Features` to explicit columns or keep them in a JSON column? (Proposed: a curated
   set of common features as real columns for indexing; the rest in `attributes` JSON.)
2. Is `PortalListing`↔`Property` dedup in scope for MVP? (See doc 01 Q1 / doc 03 §Dedup.)
3. Should `attributes` values be strings only, or typed variants? (Proposed: strings, with the
   Normalizer responsible for canonicalizing units; typed promotion when a filter matures.)
