# 014 — Model the full condition tree; expose AND-only in the MVP UI

> Status: **Accepted** · Date: 2026-07-04

## Context

Users will eventually want boolean logic beyond a flat AND of conditions (e.g. "province = Pontevedra
AND (has_lift OR has_parking)"). Building the full AND/OR/NOT tree UI is real product/UX work; building
only a flat list of conditions in the domain and database would mean a breaking schema/domain change
the day OR/NOT support is actually needed.

## Decision

Model the condition tree (`RuleGroup` with `ALL`/`ANY`/`NONE` operators over `AlertCondition` leaves
and nested `RuleGroup`s) fully in the domain and database from day one (doc 02 §4, doc 03
`alert_condition`). The **MVP UI/CLI exposes only a single top-level `ALL` group** (equivalent to
AND-only) — the full tree exists structurally but isn't surfaced to the user yet.

## Consequences

- When boolean groups ship (V3, per roadmap), it is a UI/CLI feature addition — the domain model,
  persistence schema, and Rule Engine (which already evaluates arbitrary nesting, doc 04 §2) need no
  change.
- The MVP's user-facing complexity stays low (one flat list of conditions to fill in) while the
  underlying model is never revisited.
- The `alert_condition` table's self-referential tree (`parent_group_id`) is slightly more complex than
  a flat conditions table would be, accepted specifically to avoid the alternative below.

## Alternatives considered

- **Flat list of conditions (AND-only) in both domain and schema for the MVP** — rejected: the day
  OR/NOT is needed, both the domain model and the database schema would need a breaking migration,
  plus every piece of code that assumed "conditions is a flat list" (factory, engine, persistence).
  Modeling the tree now and hiding it in the UI costs almost nothing extra today and avoids that
  rewrite entirely.

## Revisit when

The V3 roadmap item "full boolean condition builder in UI" is picked up — this ADR is the reason that
work is UI/CLI-only, not domain/schema work.
