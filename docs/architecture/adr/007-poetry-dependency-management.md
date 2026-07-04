# 007 — Dependency management: pip + setuptools, not Poetry

> Status: **Accepted** · Date: 2026-07-04

## Context

Phase 1 needed a way to declare the project's dependencies, install them (with a dev extra for
tooling), and build a distributable/installable package for the Docker image. Poetry is a common,
capable choice in the Python ecosystem — a single tool for dependency resolution, virtualenv
management, lock-file-based reproducibility, and PyPI publishing. This project also considered it, and
this ADR records why it was **not** adopted, at least for now.

## Decision

Use **plain `pyproject.toml`** with the standard `setuptools` build backend (`[build-system]`),
`pip install -e ".[dev]"` for local development, and no lock file. All tool configuration (ruff,
black, mypy, pytest, coverage, import-linter) lives in the same `pyproject.toml` under their
respective `[tool.*]` tables, each documented inline — see
[../../../pyproject.toml](../../../pyproject.toml).

This was implemented and verified in Phase 1 (issue #2): the package installs, imports, and all
quality tools run against it, in CI and in Docker, without Poetry.

## Consequences

- One fewer tool to install and learn for anyone cloning the repo — `pip install -e ".[dev]"` works
  with the Python that ships on any machine with 3.12+, no separate Poetry install/version to manage.
- No `poetry.lock` means dependency versions aren't pinned to an exact resolved graph; reproducibility
  relies on the version ranges declared in `pyproject.toml` plus CI catching breakage quickly. This is
  an accepted trade for a project with a small, slow-moving dependency set and no external consumers
  depending on a published package.
- The project is **not** published to PyPI and has no need for Poetry's publishing workflow
  (`poetry publish`) — the thing Poetry is strongest at is not a requirement here.
- The Dockerfile and CI both already depend on this choice (`pip install -e .` in both); adopting
  Poetry later means touching both, plus regenerating a lock file, plus re-verifying the whole Phase 1
  pipeline — a real migration, not a config tweak.

## Alternatives considered

- **Poetry** — stronger dependency resolution and a lock file for fully reproducible installs, native
  virtualenv management, and a smoother publish workflow. Rejected for now: this project doesn't
  publish a package, has a small dependency surface where resolution conflicts are unlikely, and
  adding Poetry today would mean migrating already-verified, CI-green tooling (Dockerfile, CI
  workflow, pre-commit) for a benefit (lock-file reproducibility) that matters more once dependencies
  or contributors multiply.
- **PDM** — similar trade-offs to Poetry (lock file, PEP 621-native); rejected for the same reason —
  no current need outweighs the migration cost.
- **Pipenv** — older, generally superseded by Poetry/PDM in current practice; not seriously considered.
- **`uv`** — very fast installs and increasingly common, and the least disruptive *future* option
  since it can consume the existing `pyproject.toml` largely as-is. Noted as the most likely candidate
  if this decision is revisited, rather than Poetry.

## Revisit when

The dependency set grows enough that version-resolution conflicts become a recurring problem, or the
project gains external consumers who need a reproducible, pinned install (a published package, a
second team member with a different environment) — at that point re-evaluate `uv` first, Poetry
second.
