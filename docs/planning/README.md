# Project Planning

The live plan lives on GitHub — this document is the map to it.

- **Project board:** [Real Estate Alert Platform (Project #3)](https://github.com/users/alopezmoreira1989/projects/3)
- **Issues:** https://github.com/alopezmoreira1989/real_estate_tracker/issues
- **Phased roadmap (source of truth for ordering):** [../roadmap.md](../roadmap.md)

## Structure

**Epics** are expressed as `epic:*` labels; **Phases** are GitHub **milestones**; **Issues** carry
`epic:*`, `type:*`, `complexity:*`, and (where MVP-critical) `priority:mvp` labels. Every issue has a
description, acceptance criteria, dependencies, complexity, and a suggested order in its body.

### Labels

**Epics** — which part of the system an issue belongs to:
`arch` · `db` · `rule-engine` · `normalization` · `scrapers` · `notifications` · `scheduler` ·
`api` · `frontend` · `deploy` · `testing` · `docs` · `perf`

**Type** — the shape of the work:

| Label | Meaning |
|-------|---------|
| `type:feature` | New capability |
| `type:infra` | Tooling / infrastructure (no user-facing behavior change) |
| `type:test` | Testing work (fixtures, coverage, golden tests) |
| `type:chore` | Chore / maintenance (docs, cleanup, non-functional) |

**Complexity** — rough sizing, used for planning, not a commitment:

| Label | Meaning |
|-------|---------|
| `complexity:S` | ≤ half a day |
| `complexity:M` | 1–2 days |
| `complexity:L` | 3–5 days |

**Priority:**

| Label | Meaning |
|-------|---------|
| `priority:mvp` | Required for the MVP (roadmap Phase 7 exit criteria) — everything else is V2/V3 or non-blocking polish |

## Milestones (phases)

| Milestone | Issues | Theme |
|-----------|--------|-------|
| Phase 1: Foundation & Tooling | #1–#5 | skeleton, tooling, CI, Docker |
| Phase 2: Domain & Persistence | #6–#11 | VOs, vocab, aggregates, ORM, repos |
| Phase 1.5: Project Hardening | #39 | ADRs, diagrams, README, DX docs, CI/tooling polish — no business logic; developed alongside Phase 2/3 |
| Phase 3: Rule Engine | #12–#17 | Specification, registry, operators, factory, engine — code-complete on `dev_alm`, PR pending |
| Phase 4: Normalization | #18–#22 | RawListing→Property, parsers, vocab dicts |
| Phase 5: Idealista Scraper & Search | #23–#28 | scraper, capabilities, planner, cache, RunAlertCycle |
| Phase 6: Telegram Notifications | #29–#31 | outbox, notifier, dispatcher |
| Phase 7: Scheduler (MVP) | #32–#34 | APScheduler, coalescing, CLI — **MVP** |
| Phase 8: Frontend (Dashboard) | #35–#36 | Streamlit + verify-on-dev_alm workflow |
| V2: Breadth & Robustness | (backlog) | more portals, dedup, FastAPI, Postgres |
| V3: Product & Scale | (backlog) | multi-user, boolean UI, price trends, geo |

## Using the GitHub Project board

The [project board](https://github.com/users/alopezmoreira1989/projects/3) is a GitHub Projects (v2)
board with every repo issue added as an item:

- **Group by milestone** to see phase-by-phase progress; **group by `epic:*` label** to see
  cross-phase work on one subsystem (e.g. every `scrapers`-labeled issue regardless of phase).
- An issue's **status** (Todo / In Progress / Done) reflects its actual state — move it when you
  start/finish work, don't rely on labels alone for status.
- New issues: use the [issue templates](../../.github/ISSUE_TEMPLATE/) (bug/feature/question) — they
  apply the right starting labels. Add the issue to the project board and set its milestone/epic
  labels per the tables above.

## Release process

See [CONTRIBUTING.md § Release process](../../CONTRIBUTING.md#release-process) — no formal releases
are tagged before the MVP milestone (Phase 7) is reached.

## Regenerating / extending

The board's labels/milestones/issues were created by `scripts/gh_setup.sh` (idempotent for
labels/milestones; re-running it re-creates issues, so don't re-run it wholesale once issues exist —
add new `ci "..."` calls for new issues only). To add issues, extend [../roadmap.md](../roadmap.md)
first, then add a matching `ci "..."` call following the existing pattern.
