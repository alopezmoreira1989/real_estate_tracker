# 012 — Notifications via an outbox table, dispatched separately from scraping

> Status: **Accepted** · Date: 2026-07-04

## Context

Driver D4: notification delivery is orthogonal to match detection and has entirely different failure
modes (a Telegram API timeout should never corrupt or block alert evaluation, and vice versa). If
notification sending happened inline inside the alert cycle, a slow or failing channel would stall
scraping/matching for every alert, not just the ones using that channel.

## Decision

New matches are written to a **notification outbox** (`notification` table, `status: PENDING → SENT |
FAILED`) inside the same transaction as the match itself. A separate **dispatcher job** polls pending
notifications, resolves the channel, sends, and updates status with retry/backoff — entirely decoupled
from the scrape/evaluate cycle. See [08-sequence-diagrams.md](../08-sequence-diagrams.md) §3 and
[ADR-005](005-telegram-notifications.md) for the first concrete channel.

## Consequences

- A channel outage (Telegram down, rate-limited) never blocks or slows the alert cycle; it only delays
  that channel's own delivery, retried independently.
- `UNIQUE(alert_id, property_id)` on `alert_match` plus outbox idempotency means a retried cycle or
  dispatcher run never double-notifies (CLAUDE.md §12).
- Adding a channel (email, Discord — V2) is a new `Notifier` adapter and `channel_type`, with no change
  to detection or the outbox mechanism itself.
- The cost is an extra table and a second scheduled job (vs. sending inline), and a small window where
  a match exists but hasn't been delivered yet — acceptable since delivery latency of seconds-to-a-
  couple-minutes is not user-visible as "wrong."

## Alternatives considered

- **Send synchronously inside the alert cycle** — rejected: couples two orthogonal concerns (D4)
  directly; a channel failure would stall or fail the entire cycle.
- **A message queue (e.g. Redis/RabbitMQ) instead of a DB outbox table** — adds an operational
  dependency with no benefit at MVP volume (single user, low message rate); the DB-outbox pattern gets
  the same decoupling with zero new infrastructure. Revisit if message volume or multi-worker delivery
  ever requires a real queue.

## Revisit when

Delivery volume or the number of independent dispatcher workers grows enough that DB-polling becomes a
bottleneck — at that point a real message queue is worth the added operational cost.
