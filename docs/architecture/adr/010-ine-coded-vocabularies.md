# 010 — Controlled vocabularies keyed by official INE codes

> Status: **Accepted** · Date: 2026-07-04

## Context

Spanish provinces and municipalities are spelled inconsistently across portals ("A Coruña" / "La
Coruña" / "Coruña"). A `Location` value object that stored free text would make `province == "..."`
alert conditions unreliable, and would make joining against any official geographic dataset fragile.

## Decision

Key `Province` and `Municipality` by their official **INE (Instituto Nacional de Estadística) codes**
(e.g. `36 = Pontevedra`), not display names. Each portal's Normalizer maps its own spelling variants to
the INE code via a vocabulary dictionary (doc 05 §3); the canonical `Location` VO only ever stores the
code.

## Consequences

- Alert conditions on province/municipality are exact and portal-independent; "Pontevedra" always
  means INE `36` regardless of which portal supplied the listing.
- Future joins against official geographic/statistical datasets (also INE-keyed) are trivial.
- Every portal needs its own name→INE-code mapping table, maintained as new spelling variants surface
  (doc 05 §5 — this is exactly the kind of drift the normalization test suite is designed to catch).

## Alternatives considered

- **Free-text province/municipality** — rejected: unreliable equality/filtering, no canonical join
  key.
- **A custom internal enum unrelated to any official code** — rejected: reinvents what INE codes
  already provide for free, with no interoperability benefit.

## Revisit when

Not expected to change.
