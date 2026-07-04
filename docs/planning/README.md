# Project Planning

The live plan lives on GitHub — this document is the map to it.

- **Project board:** [Real Estate Alert Platform (Project #3)](https://github.com/users/alopezmoreira1989/projects/3)
- **Issues:** https://github.com/alopezmoreira1989/real_estate_tracker/issues
- **Phased roadmap (source of truth for ordering):** [../roadmap.md](../roadmap.md)

## Structure

**Epics** are expressed as `epic:*` labels; **Phases** are GitHub **milestones**; **Issues** carry
`epic:*`, `type:*`, `complexity:*`, and (where MVP-critical) `priority:mvp` labels. Every issue has a
description, acceptance criteria, dependencies, complexity, and a suggested order in its body.

### Epics → labels
`arch` · `db` · `rule-engine` · `normalization` · `scrapers` · `notifications` · `scheduler` ·
`api` · `frontend` · `deploy` · `testing` · `docs` · `perf`

### Milestones (phases) — 36 issues, #1–#36
| Milestone | Issues | Theme |
|-----------|--------|-------|
| Phase 1: Foundation & Tooling | #1–#5 | skeleton, tooling, CI, Docker |
| Phase 2: Domain & Persistence | #6–#11 | VOs, vocab, aggregates, ORM, repos |
| Phase 3: Rule Engine | #12–#17 | Specification, registry, operators, factory, engine |
| Phase 4: Normalization | #18–#22 | RawListing→Property, parsers, vocab dicts |
| Phase 5: Idealista Scraper & Search | #23–#28 | scraper, capabilities, planner, cache, RunAlertCycle |
| Phase 6: Telegram Notifications | #29–#31 | outbox, notifier, dispatcher |
| Phase 7: Scheduler (MVP) | #32–#34 | APScheduler, coalescing, CLI — **MVP** |
| Phase 8: Frontend (Dashboard) | #35–#36 | Streamlit + verify-on-dev_alm workflow |
| V2: Breadth & Robustness | (backlog) | more portals, dedup, FastAPI, Postgres |
| V3: Product & Scale | (backlog) | multi-user, boolean UI, price trends, geo |

## Regenerating / extending

The board was created by `scripts/gh_setup.sh` (idempotent for labels/milestones). To add issues,
extend the roadmap first, then add `ci "..."` calls following the existing pattern.
