# Development Guide

Detailed local setup and day-to-day commands. For the *process* around contributing (branches,
commits, PRs), see [CONTRIBUTING.md](CONTRIBUTING.md). For the architecture rules your code must
follow, see [CLAUDE.md](CLAUDE.md).

## Prerequisites

- **Python 3.12+.** If your machine has multiple Python versions installed (common on Windows,
  where `python`/`py` may default to an older version), create the virtualenv explicitly with the
  right one, e.g. `py -3.12 -m venv .venv`.
- Git.
- (optional) Docker + Docker Compose, if you want to run the app in a container instead of a local
  virtualenv.

## Environment setup

```bash
git clone https://github.com/alopezmoreira1989/real_estate_tracker.git
cd real_estate_tracker

python -m venv .venv
source .venv/bin/activate          # Windows (bash): source .venv/Scripts/activate
                                    # Windows (PowerShell): .venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e ".[dev]"

cp .env.example .env               # edit if you need non-default ENVIRONMENT/LOG_LEVEL
```

Verify:

```bash
python -m real_estate
python -c "import real_estate; print(real_estate.__name__)"
```

## Pre-commit hooks

Install the git hook once so `ruff`/`black`/`mypy` and basic hygiene checks run automatically on
every commit:

```bash
pre-commit install
```

`.pre-commit-config.yaml` runs the tools **against your active virtualenv** (`language: system`), so
make sure `.venv` is activated (or its `Scripts`/`bin` directory is on `PATH`) before committing —
otherwise the hooks fail with "executable not found" rather than silently skipping.

To run every hook against the whole repo on demand (not just staged files):

```bash
pre-commit run --all-files
```

## Day-to-day commands

```bash
ruff check .              # lint (add --fix to auto-fix what's safe to auto-fix)
black .                   # format
mypy                      # strict type-check
lint-imports               # architecture boundary contracts (pyproject.toml [tool.importlinter])
pytest                    # tests + coverage (term-missing report)
pytest --cov-report=html  # HTML coverage report -> htmlcov/index.html
pytest tests/unit/path/to/test_file.py::test_name   # run a single test
```

## Running the Streamlit dashboard

The dashboard (`src/real_estate/presentation/web/app.py`, bootstrapped by
`src/real_estate/dashboard.py`) is the **manual-verification surface for `dev_alm`** before any
merge to `main` (CLAUDE.md §9) — from Phase 8 on, "run the dashboard and look at it" is a real step,
not an aspirational one. It calls the exact same application use-cases as the CLI, so what you see
there is what the platform actually does.

```bash
alembic upgrade head                              # schema must exist first
streamlit run src/real_estate/dashboard.py         # opens http://localhost:8501
```

Or use the helper script, which does both:

```bash
scripts/run_dashboard.sh
```

**The `dev_alm → main` verification flow:**

1. Land your work on `dev_alm` (issue-by-issue commits, full quality gate green on each).
2. Run the dashboard (`scripts/run_dashboard.sh` or the two commands above) against a local DB —
   seed it via the CLI (`python -m real_estate alerts create ...`) or `python -m real_estate
   run-cycle` if you want a real scrape.
3. Walk through what changed: create/edit an alert, check Matches shows real data, check Health
   shows the expected execution/issue counts, check Channels. A blank or erroring tab is a sign
   something regressed even if the test suite is green — this is *whole-system* eyeballing, not a
   substitute for the automated gate.
4. Only once it looks right, open the `dev_alm → main` PR (CI green) and merge.

## Docker

```bash
docker build -t real-estate .
docker compose build
docker compose up -d app             # starts the scheduler daemon (mirrors CI's smoke test)
docker compose logs app              # check it came up cleanly
docker compose down                  # stop it
docker compose config                # validate the compose file without running anything
```

## Troubleshooting

- **`mypy`/`ruff`/`black` "not found" in a pre-commit hook** — your virtualenv isn't on `PATH` in the
  shell that invoked `git commit`. Activate `.venv` first.
- **Wrong Python version picked up (`python --version` shows < 3.12)** — on Windows, the `python`
  command may be a Microsoft Store alias stub, or a much older interpreter may be first on `PATH`.
  Use `py -3.12 -m venv .venv` to pin the interpreter explicitly when creating the virtualenv.
- **`import-linter` fails with "must have include_external_packages=True"** — only relevant if you're
  editing `[tool.importlinter]` yourself; the third-party-forbidding contract needs that root-level
  setting (already present) to see imports of packages outside `real_estate`.
- **Coverage warnings ("Module real_estate was never imported")** — harmless if you ran `pytest` on a
  subset of tests that happens not to import the package (e.g. a single non-package test file); run
  the full `pytest` for an accurate report.

## Editor setup

No specific editor is required. If using VS Code, enabling format-on-save with Black and pointing the
Python extension's interpreter at `.venv` will mirror what CI enforces.
