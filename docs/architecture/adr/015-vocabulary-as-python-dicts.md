# 015 — Normalizer mapping/vocabulary tables as typed Python dicts

> Status: **Accepted** · Date: 2026-07-04

## Context

Each portal Normalizer needs field-mapping tables (`precio` → `price`) and vocabulary dictionaries
(`"Suelo urbanizable"` → `LandType.URBANIZABLE`). These could live as code (Python dicts) or as
external data (YAML/JSON), each with different editability and safety trade-offs. Today, the only
person editing these mappings is the developer who also writes the normalizer code.

## Decision

Keep mapping/vocabulary tables as **typed Python dicts** co-located with each portal's normalizer
package (doc 05 §3), not YAML or another external format, for as long as a developer (not a non-technical
operator) owns them.

## Consequences

- Mappings are type-checked (mypy catches a typo'd enum member at commit time, not at runtime against
  live data), directly unit-testable (`assert map("Suelo urbanizable") is URBANIZABLE`), and
  refactor-safe (renaming an enum member is a single IDE refactor, not a grep across YAML files).
- No YAML parsing/schema-validation layer is needed.
- The cost: a non-technical operator cannot edit vocabulary without a code change and a deploy. This is
  accepted because no such operator exists yet — see *Revisit when*.

## Alternatives considered

- **YAML/JSON config files** — more editable without touching Python, and arguably friendlier for a
  future non-developer maintaining mappings. Rejected for now: adds a parsing/validation layer for a
  benefit (non-developer editability) that has no current user. Explicitly the fallback choice if that
  changes.

## Revisit when

A non-developer needs to maintain or extend portal mappings — at that point move to YAML (or a small
admin UI) as originally deferred.
