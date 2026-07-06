## Summary

<!-- What changed and why. Link the issue: Closes #NN -->

## Which layer(s) does this touch?

<!-- domain / application / infrastructure / presentation / tooling / docs -->

## Test plan

<!-- What you ran to verify this. Check what applies; delete what doesn't. -->

- [ ] `pytest` passes locally
- [ ] `ruff check .` / `black --check .` / `mypy` pass locally
- [ ] `lint-imports` passes (no architecture boundary violations)
- [ ] Added/updated tests for the behavior change (CLAUDE.md §8: a bug fix ships with a test that
      fails without the fix)
- [ ] Verified manually (describe how) — required if this touches presentation or a runnable flow

## Architecture notes

<!--
- Does this add a new pattern, port, or dependency? Point to the ADR, or note that one is needed.
- Does this follow the dependency rule (CLAUDE.md §6)? import-linter should catch violations, but
  call out anything non-obvious (e.g. a new third-party dependency the domain-purity contract needs
  to know about — pyproject.toml [tool.importlinter], "Domain does not depend on third-party
  frameworks").
-->

## Checklist

- [ ] Commit messages follow [Conventional Commits](../CONTRIBUTING.md#commit-messages--conventional-commits)
- [ ] Relevant docs updated (design doc, ADR, roadmap) if this changes behavior described there
- [ ] Targets `dev_alm` (not `main`), unless this is the `dev_alm` → `main` promotion PR
