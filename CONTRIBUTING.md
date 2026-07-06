# Contributing

Thanks for considering a contribution. This document covers the **process** — branch strategy,
commit conventions, and how a PR gets merged. For **how the code must be structured** (layers,
dependency rules, naming, testing philosophy), read [CLAUDE.md](CLAUDE.md) first — it is the source
of truth and every PR is expected to follow it. For **local machine setup**, see
[DEVELOPMENT.md](DEVELOPMENT.md).

## Before you start

- Check [open issues](https://github.com/alopezmoreira1989/real_estate_tracker/issues) and
  [docs/roadmap.md](docs/roadmap.md) — work is organized into phases/milestones, and later phases
  assume earlier ones exist. If you want to work on something not yet an issue, open one first
  (see the [issue templates](.github/ISSUE_TEMPLATE/)) so the approach can be agreed before code is
  written.
- Read [docs/architecture/README.md](docs/architecture/README.md) and the ADRs in
  [docs/architecture/adr/](docs/architecture/adr/) relevant to what you're touching — a PR that
  contradicts an accepted ADR needs either a new ADR superseding it or a rework.

## Branch strategy

- **`main`** is always releasable and protected. It only receives reviewed, CI-green merges — never
  commit directly to it.
- **`dev_alm`** is the integration branch. Day-to-day work happens here, or in a short-lived
  **`feature/<epic>-<short-desc>`** branch off it for larger issues (squash-merged back into
  `dev_alm`).
- `dev_alm` is promoted to `main` once CI is green and (from Phase 8 onward) the change has been
  exercised via the Streamlit dashboard.

```
feature/* ──▶ dev_alm ──(CI green + manual verification)──▶ main
```

## Commit messages — Conventional Commits

`type(scope): summary`, imperative mood, ≤72-character subject, body explains **why** (not just
what), and references the issue it closes.

- `type` ∈ `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`
- `scope` is an epic/layer: `rule-engine`, `normalization`, `scraper`, `db`, `infra`, `api`, `arch`, …

```
feat(rule-engine): add BETWEEN operator strategy

Alerts need inclusive range filters (e.g. price between X and Y); BETWEEN
was the one comparison operator missing from doc 04 §4.

Closes #17
```

## Pull requests

- Keep PRs **small and focused** — one issue, one concern. A PR description states what was
  verified (tests run, manual check performed), links the issue, and calls out any deviation from
  the linked design doc/ADR.
- CI (lint, `mypy --strict`, import-linter, tests) must be green before merge. Merges to `main`
  only come from `dev_alm`.
- Use the [PR template](.github/pull_request_template.md) — it's applied automatically.
- New filters, portals, or notification channels are almost always **additive** changes (register a
  `FieldDescriptor`, add a co-located portal package, add a `Notifier` adapter) rather than edits to
  shared engine code — see CLAUDE.md §2 and §7. If your change edits the Rule Engine, a Normalizer
  registry, or the composition root to add a new *kind* of thing, double check it couldn't instead be
  a registration.

## Code quality gates

Run before opening a PR (see [DEVELOPMENT.md](DEVELOPMENT.md) for setup):

```bash
pre-commit run --all-files   # ruff, black, mypy, plus hygiene hooks
pytest                        # full test suite + coverage
lint-imports                  # architecture boundary contracts
```

A bug fix ships with a test that fails without the fix (CLAUDE.md §8) — coverage is a signal, not a
target in itself.

## Release process

The project has not tagged a formal release yet — versioning starts once the MVP is reached
(roadmap Phase 7 exit criteria: unattended scheduled operation for one user). Until then, `main`
represents the current state of the platform and is the only thing considered "released." Once the
MVP ships, releases will be tagged (`vX.Y.Z`, [SemVer](https://semver.org/)) from `main`, with a
changelog generated from Conventional Commit history.

## Reporting bugs / requesting features

Use the [issue templates](.github/ISSUE_TEMPLATE/) — bug report, feature request, or question. See
[docs/planning/README.md](docs/planning/README.md) for how issues map to epics, milestones, and the
GitHub Project board.

## Code of Conduct

Participation in this project is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
