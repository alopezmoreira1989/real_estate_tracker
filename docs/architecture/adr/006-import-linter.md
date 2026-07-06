# 006 — Enforce the dependency rule mechanically with import-linter

> Status: **Accepted** · Date: 2026-07-04

## Context

[ADR-001](001-clean-architecture.md) commits the project to an inward-only dependency rule between
domain, application, infrastructure, and presentation. A rule that only exists as documentation and
code-review discipline erodes the first time someone is in a hurry: a single `import sqlalchemy` typo
inside `domain/model/` would compile, pass tests, and silently reintroduce the exact coupling the
architecture exists to prevent. Given this is frequently a single-engineer project, there is no
guaranteed second reviewer to catch it.

## Decision

Enforce the dependency rule with **`import-linter`**, configured in `pyproject.toml`
(`[tool.importlinter]`), running as a required step in CI ([.github/workflows/ci.yml](../../../.github/workflows/ci.yml))
and available locally via `lint-imports`. Contracts encode, precisely:

1. `domain` may import nothing from `application`, `infrastructure`, or `presentation`, **and**
   nothing from the third-party frameworks the domain must never depend on directly (`sqlalchemy`,
   `pydantic`, `structlog`, `telegram`, `httpx`, `playwright`, `fastapi`, `typer`) — this is the literal
   "domain imports only the standard library" rule from CLAUDE.md §2, checked automatically rather
   than trusted.
2. `application` may not import `infrastructure` or `presentation`.
3. `presentation` may not import `infrastructure` directly (it goes through `application`).
4. `infrastructure` may not import `presentation`.

A broken contract fails CI (`lint-imports` exits non-zero); see
[docs/architecture/09-diagrams.md](../09-diagrams.md) for the enforced dependency graph.

## Consequences

- A boundary violation is caught in seconds, in CI, on the exact commit that introduced it — not
  discovered weeks later while debugging why `domain` suddenly needs a database connection to import.
- The contract list is itself living documentation of the architecture: reading `[tool.importlinter]`
  tells a new contributor the dependency rule precisely, with no ambiguity about "does application
  count as inside or outside."
- New layers or sub-packages that need their own boundary (e.g. co-located portal packages under
  `infrastructure/scrapers/<portal>/` not depending on each other) can add an `independence` contract
  later without changing the existing ones.
- The cost is a few seconds added to CI and a small amount of contract-maintenance whenever a
  genuinely new cross-layer dependency is intentionally introduced (which itself is a useful forcing
  function to double-check the design).

## Alternatives considered

- **Code review discipline only** — zero tooling cost, but relies on every reviewer catching every
  violation, every time; does not scale past the first missed review, and this project frequently has
  no second reviewer at all. Rejected.
- **A custom AST-walking script** — full control over the rule shape, but reinvents a well-maintained
  tool for no additional expressiveness the project needs. Rejected.
- **`pydeps` / dependency-graph visualization only** — good for understanding an existing graph, but
  does not *fail the build*; it is a diagnostic tool, not an enforcement one. Kept in mind as a
  possible addition for visualizing the graph, not a replacement for import-linter's pass/fail
  contracts.
- **Deptry** (unused-dependency detection) — solves a different problem (dead dependencies in
  `pyproject.toml`), not layer boundaries; could be added later but does not substitute for
  import-linter here.

## Revisit when

If a new physical layer or bounded context is introduced (ADR-002 "Revisit when"), add the
corresponding contract in the same pass, not after the fact.
