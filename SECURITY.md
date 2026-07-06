# Security Policy

## Supported versions

The project is pre-MVP (see [docs/roadmap.md](docs/roadmap.md)) and has not tagged a release yet.
Only the tip of **`main`** is supported — please make sure you're on the latest commit before
reporting an issue.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security vulnerability. Instead:

- Use GitHub's [private vulnerability reporting](https://github.com/alopezmoreira1989/real_estate_tracker/security/advisories/new)
  for this repository, or
- Email **al.lopez.moreira@gmail.com** with a description of the issue, steps to reproduce, and its
  potential impact.

You should expect an acknowledgement within a few days. As a single-maintainer project there is no
formal SLA, but security reports are treated as the highest priority.

## Scope

In scope: anything that could compromise a user's data, credentials, or notification channel
secrets (e.g. a Telegram bot token) — injection vulnerabilities, secret leakage in logs, insecure
deserialization, dependency vulnerabilities with a real exploit path, etc.

Out of scope / handled elsewhere:

- **Portal scraping legality/ethics** (robots.txt, rate limiting, terms of service) is a compliance
  concern addressed in [CLAUDE.md](CLAUDE.md) §14, not a security vulnerability in this project's
  code. If you believe a scraper behaves abusively toward a portal, please open a regular issue.
- Vulnerabilities in third-party dependencies with no known exploit path affecting this project —
  please still report them, but they'll be triaged as routine dependency updates (Dependabot is
  enabled) rather than security incidents.

## Handling of secrets

Per [CLAUDE.md](CLAUDE.md) §14: secrets (Telegram bot tokens, future DB credentials) are supplied via
environment variables or a git-ignored `.env` file (see [.env.example](.env.example)) and are never
committed. Notification channel secrets are encrypted at rest once persistence exists (Phase 2+).
