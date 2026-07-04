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

## Docker

```bash
docker build -t real-estate .
docker compose build
docker compose run --rm app          # one-shot run (mirrors CI's smoke test)
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
