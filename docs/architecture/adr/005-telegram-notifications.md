# 005 — Telegram as the first notification channel

> Status: **Accepted** · Date: 2026-07-04

## Context

A matched listing is only useful if the user actually sees it promptly (driver D4: notifications are
orthogonal to scraping, but they are the point of the product). The MVP is single-user, run by the
person operating it, so the channel needs to be near-zero-setup, free, and immediate. Candidate
channels include Telegram, email (SMTP), SMS, push notifications, and Discord/Slack-style webhooks —
the roadmap already plans email and Discord for V2 (docs/roadmap.md).

## Decision

Ship **Telegram** as the only notification channel for the MVP, via a bot created through
`@BotFather` and the Telegram Bot HTTP API. `NotificationChannel.channel_type = TELEGRAM` stores the
chat id (encrypted, per CLAUDE.md §14); `TelegramNotifier` implements the domain's `Notifier` port
(ADR-001) and is the only infrastructure module that talks to Telegram's API.

Rationale for Telegram specifically:

- **Zero-friction setup** — no app-store review, no domain/SMTP reputation to manage, no phone number
  registration; a bot token and a chat id are enough.
- **Free, generous rate limits** for the message volume this platform produces (per-alert-cycle
  matches, not high-frequency chat).
- **Rich-enough formatting** (Markdown/HTML messages, images) to show a listing's price, area, and a
  link/photo without building a web view.
- **Already installed** for the target user (personal use, Spanish real-estate market — Telegram is
  widely used here), unlike a bespoke mobile app.

## Consequences

- The notification **outbox pattern** ([ADR-012](012-notification-outbox.md)) already decouples match
  detection from delivery, so Telegram being the only channel today does not block adding Email or
  Discord later — each new channel is a new `Notifier` adapter plus a `channel_type` value, with no
  change to detection, matching, or the outbox itself.
- Telegram Bot API failures (rate limits, blocked bot, invalid chat id) must be handled at the adapter
  boundary per CLAUDE.md §12 — retried with backoff, and surfaced via `notification.last_error`
  without corrupting match detection.
- The MVP has exactly one channel type in production use; multi-channel fan-out per user (send the
  same match to Telegram *and* email) is a V2 concern, not designed against yet beyond the schema
  already allowing multiple `NotificationChannel` rows per user.

## Alternatives considered

- **Email (SMTP)** — universal, but needs sender reputation/SPF/DKIM setup to avoid spam folders, and
  is slower to notice than a phone push. Deferred to V2 once multi-channel fan-out matters.
- **Native push notifications (e.g. via a companion mobile app)** — requires building and maintaining
  a mobile client just to receive alerts; disproportionate to a personal/MVP use case. Rejected for
  now.
- **Discord webhook** — as easy to integrate as Telegram, but assumes the user already lives in
  Discord; Telegram was judged the better default for the Spanish real-estate use case. Planned as a
  V2 addition alongside email, not a replacement.

## Revisit when

Multi-user (V3) or multi-channel-per-user delivery preferences become a real requirement — at that
point channel selection/fan-out logic in the dispatcher (doc 08 §3) needs explicit design, not just
"the one channel a user configured."
