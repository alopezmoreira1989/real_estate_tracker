# 05 — Data Normalization Strategy

> Status: **Draft for review** · Owner: Architecture · Depends on:
> [02-domain-model.md](02-domain-model.md)

Driver **D2**: portals disagree on field names, units, and vocabularies. Normalization is the single
seam where that chaos is contained. After this layer, **nothing knows a portal exists**.

---

## 1. The contract: `RawListing` → `Property`

```
Scraper (per portal)  ──▶  RawListing  ──▶  Normalizer (per portal)  ──▶  Property (canonical)
```

- **`RawListing`** — a faithful capture: `portal_id`, `external_id`, `url`, `scraped_at`, and a
  `raw: Mapping[str, Any]` of *exactly what the portal gave us* (its keys, its units, its strings).
  **No cleaning happens in the scraper.** This makes scrapers dumb and testable, and lets us
  re-normalize historical `raw_payload` (doc 03) when a mapping improves.
- **`Normalizer`** — a domain **Port** implemented per portal in infrastructure (an **Adapter**). It
  is the *only* component allowed to know portal-specific field names and value spellings.

```python
class Normalizer(Protocol):                 # domain port
    portal_slug: str
    def normalize(self, raw: RawListing) -> NormalizationResult: ...

@dataclass
class NormalizationResult:
    property: Property | None                # None if unmappable & undroppable
    issues: list[NormalizationIssue]         # warnings: unmapped field, fallback used, ...
```

---

## 2. Anatomy of a Normalizer (four ordered concerns)

A normalizer is deliberately composed of four small, testable steps rather than one big function:

1. **Field mapping** — portal key → canonical field.
   `precio|importe|price → price`, `superficie|metros|size → area`,
   `habitaciones|dormitorios|rooms → rooms`, `ascensor|lift → features.has_lift`.
   Implemented as a declarative **mapping table** per portal (data, not code).

2. **Value parsing (units & formats)** — portal string → typed VO.
   `"120.000 €" → Money(120000, EUR)`, `"3.000 m²" → Area(3000)`, `"1.234,56" → Decimal` (Spanish
   thousands/decimal separators). Centralized parsers (`parse_money`, `parse_area`, `parse_int`)
   shared across portals — this is the DRY core of normalization.

3. **Vocabulary mapping** — portal free text → controlled enum (doc 02).
   `"Suelo urbanizable" → LandType.URBANIZABLE`, `"Piso" → PropertyType.FLAT`,
   `"Pontevedra" → province_ine 36`. Backed by **dictionary tables** per vocabulary. Unknown value ⇒
   map to `OTHER`/`UNKNOWN` **and emit an issue** (never silently drop — doc 02 §3).

4. **Derivation & assembly** — compute derived fields (`price_per_m2 = price / area`), assemble the
   `Property`, and validate invariants (VO constructors enforce ranges/units).

```
raw ─▶ [FieldMapper] ─▶ canonical dict ─▶ [ValueParser] ─▶ typed values
    ─▶ [VocabularyMapper] ─▶ controlled values ─▶ [Assembler+Derive] ─▶ Property
```

---

## 3. Mapping tables as data

Field maps and vocabulary dictionaries live as **declarative config** (Python dicts / YAML) per
portal, not as imperative code:

```python
IDEALISTA_FIELD_MAP = {
    "price": "price", "size": "area", "rooms": "rooms",
    "bathrooms": "bathrooms", "lift": "features.has_lift",
    "propertyType": "property_type", "detailedType": "land_type_hint",
    "municipality": "municipality", "province": "province", ...
}

PROPERTY_TYPE_VOCAB = {                    # shared canonical dictionary
    "piso": PropertyType.FLAT, "flat": PropertyType.FLAT,
    "casa": PropertyType.HOUSE, "chalet": PropertyType.CHALET,
    "suelo": PropertyType.LAND, "terreno": PropertyType.LAND, ...
}
```

Benefits: a new portal is mostly *new tables* + a thin scraper, reviewers can diff mappings, and the
mappings are directly unit-testable (`assert map("Suelo urbanizable") is URBANIZABLE`).

---

## 4. Selecting the right Normalizer — Registry + Factory

```python
class NormalizerRegistry:
    def register(self, normalizer: Normalizer) -> None: ...   # keyed by portal_slug
    def for_portal(self, portal_slug: str) -> Normalizer: ...
```

The application layer, given a `RawListing`, asks the registry for the matching normalizer. Portals
self-register at composition time (Factory + Registry pattern), so adding a portal never edits a
central switch statement (OCP).

---

## 5. Handling the messy reality

| Problem | Strategy |
|---------|----------|
| Missing field | leave VO `None` (tri-state); do **not** invent defaults. |
| Ambiguous property type | use portal's detailed subtype hint; fall back to `OTHER` + issue. |
| Locale numbers (`1.234,56`) | dedicated Spanish-aware parsers; never rely on `float(str)`. |
| Province name variants ("A Coruña"/"La Coruña") | vocabulary dict → INE code (doc 02). |
| Currency other than EUR | `Money` carries currency; parser detects symbol. |
| Portal changes its HTML/JSON | scraper contract test fails fast; `raw_payload` lets us re-map. |
| Land type only in description | optional per-portal enrichment step (regex over description) with an issue flag; explicitly best-effort. |

**Golden principle:** normalization is *lossy toward canonical, lossless toward raw*. We always keep
`raw_payload` (doc 03) so a better mapping can be applied retroactively.

---

## 6. Observability

Every `NormalizationIssue` (unmapped field, fallback vocabulary, failed parse) is logged with
`portal_slug`, `external_id`, and the offending value, and counted per `SearchExecution`. A rising
"unmapped vocabulary" rate is the early-warning signal that a portal changed or a mapping is
incomplete — surfaced on the dashboard rather than silently degrading match quality.

---

## 7. Testing strategy

- **Recorded fixtures**: store real `RawListing` samples per portal (sanitized) as golden inputs;
  assert the exact `Property` output. These double as regression tests when portals change.
- **Parser unit tests**: locale numbers, currency symbols, area units, edge/empty values.
- **Vocabulary coverage tests**: every known portal value maps to a non-`OTHER` canonical value
  (fails when a portal introduces a new term we haven't mapped).
- **Property invariants**: normalized output always constructs valid VOs or yields an issue.

### Capturing a scraper fixture for a new portal (process, established Phase 5)

The scraper's HTML→`RawListing` step is tested against a **real saved page**, never a synthetic one
we invent — a hand-written fixture only tests the parser against our own assumption of a portal's
markup, which can't catch a real mismatch. Process for each new portal:

1. A human opens a representative search-results page on the live site and saves it (browser
   "Save Page As → Webpage, HTML only") — no automated/unattended scraping of the live site
   (CLAUDE.md §14).
2. The saved file goes in `tests/fixtures/<portal>/search_results_page.html` (only the `.html` file;
   the accompanying saved-assets folder — images/CSS — isn't needed and isn't committed).
3. The scraper's card selectors and URL pattern are built/verified directly against that file; the
   contract test loads it and asserts sane extracted values for at least one known listing.
4. Anything not observable on the captured page (e.g. a field only shown on some listing types) is
   left unimplemented and documented as inferred/unverified rather than guessed silently — see
   `infrastructure/scrapers/idealista/field_labels.py` for the pattern.

This is the same process for every future portal (Fotocasa, Pisos.com, … — V2), not something
improvised per portal.

---

## 8. Open questions for review

1. Mapping tables in **Python dicts** (typed, testable, refactor-safe) vs **YAML** (editable without
   code)? (Proposed: Python dicts for MVP; YAML only if non-devs will edit mappings.)
2. Description-based enrichment (regex for land type/keywords) in MVP or later? (Proposed: later;
   keep normalizers deterministic first.)
3. Do we re-normalize historical `raw_payload` automatically on mapping changes, or on demand?
   (Proposed: a manual/CLI backfill command initially.)
