"""Repository ports.

The domain speaks in collections of aggregates, not SQL. Infrastructure
provides concrete adapters (e.g. ``SqlAlchemyAlertRepository``). Repositories
are always scoped by ``user_id`` where the entity is user-owned (multi-tenant,
driver D5) — enforced by the adapters.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import (
    AlertId,
    MatchId,
    NotificationChannelId,
    NotificationId,
    PropertyId,
    UserId,
)
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.notification import Notification
from real_estate.domain.model.notification_channel import NotificationChannel
from real_estate.domain.model.property import Property

# Re-exported (not just used internally): domain/ports/__init__.py forwards these so callers can
# keep importing them from real_estate.domain.ports, as they could when SearchExecutionStatus was
# defined in this module directly. Explicit `as` alias satisfies mypy strict's no-implicit-reexport.
from real_estate.domain.model.search_execution import SearchExecution as SearchExecution
from real_estate.domain.model.search_execution import SearchExecutionStatus as SearchExecutionStatus


class AlertRepository(Protocol):
    """Persistence of the :class:`SearchAlert` aggregate."""

    def add(self, alert: SearchAlert) -> None: ...

    def get(self, alert_id: AlertId) -> SearchAlert | None: ...

    def list_for_user(self, user_id: UserId) -> Sequence[SearchAlert]: ...

    def list_due(self, *, now: datetime) -> Sequence[SearchAlert]:
        """Active alerts whose ``last_run_at + frequency_seconds <= now``
        (or that have never run) — the scheduler's due-set (doc06 §5), backed
        by the ``(is_active, last_run_at)`` index (doc03).
        """
        ...


class PropertyRepository(Protocol):
    """Persistence of canonical :class:`Property` entities.

    ``add`` upserts by id and, as an infrastructure-only side effect, appends
    a ``PriceHistory`` row when the price changed — ``PriceHistory`` is not a
    domain entity (a persistence audit trail only), so this needs no separate
    port method (docs/architecture/03-database.md).
    """

    def add(self, prop: Property) -> None: ...

    def get(self, property_id: PropertyId) -> Property | None: ...


class MatchRepository(Protocol):
    """Idempotent persistence of :class:`AlertMatch` facts.

    Relies on the ``UNIQUE(alert_id, property_id)`` constraint (doc03) — a
    re-evaluation of the same candidates never double-persists a match.
    """

    def add_if_new(self, match: AlertMatch) -> MatchId | None:
        """Persist ``match`` if it doesn't already exist.

        Returns the newly persisted match's id, or ``None`` if it already
        existed — callers (e.g. notification enqueueing) need the real id of
        a *new* match, not just a new/duplicate flag.
        """
        ...

    def get(self, match_id: MatchId) -> AlertMatch | None: ...

    def list_recent_for_user(self, user_id: UserId, *, limit: int) -> Sequence[AlertMatch]:
        """Most recent matches across every alert owned by ``user_id``, scoped
        via ``search_alerts.user_id`` (matches carry no ``user_id`` of their
        own — multi-tenant scoping, CLAUDE.md §14).
        """
        ...


class PortalListingRepository(Protocol):
    """Tracks the raw, per-portal record backing a canonical :class:`Property`."""

    def find_unchanged_property_id(
        self, portal_slug: str, external_id: str, content_hash: str
    ) -> PropertyId | None:
        """Return the already-linked property id if this exact ``content_hash``
        was already recorded for ``(portal_slug, external_id)`` — meaning
        nothing changed since the last scrape and re-normalizing can be
        skipped (doc03, doc05 §2). ``None`` means new or changed: normalize it.
        """
        ...

    def upsert(
        self,
        *,
        portal_slug: str,
        external_id: str,
        property_id: PropertyId,
        url: str,
        raw_payload: Mapping[str, Any],
        content_hash: str,
        scraped_at: datetime,
    ) -> None: ...

    def get_url_for_property(self, property_id: PropertyId) -> str | None:
        """Return the originating listing url for ``property_id``, if known.

        Used to build a notification message's link (doc08 §3) without the
        domain ``Property`` itself needing to carry a portal-specific url.
        """
        ...


class NotificationChannelRepository(Protocol):
    """Persistence of a user's :class:`NotificationChannel` delivery targets.

    Adapters encrypt/decrypt ``target`` at rest transparently (CLAUDE.md §14)
    — the domain always sees a plain value.
    """

    def add(self, channel: NotificationChannel) -> None:
        """Upsert ``channel`` by id."""
        ...

    def get(self, channel_id: NotificationChannelId) -> NotificationChannel | None: ...

    def list_enabled_for_user(self, user_id: UserId) -> Sequence[NotificationChannel]: ...

    def list_for_user(self, user_id: UserId) -> Sequence[NotificationChannel]:
        """Every channel owned by ``user_id`` (enabled or not) — for
        operator/CLI listing, unlike :meth:`list_enabled_for_user` which the
        dispatcher uses to select delivery targets.
        """
        ...


class NotificationRepository(Protocol):
    """The notification outbox (doc03, doc08 §3)."""

    def enqueue(
        self, match_id: MatchId, channel_id: NotificationChannelId, *, now: datetime
    ) -> bool:
        """Enqueue a ``PENDING`` notification for ``(match_id, channel_id)``.

        Idempotent: returns whether it was newly enqueued.
        """
        ...

    def list_pending(self, limit: int) -> Sequence[Notification]: ...

    def mark_sent(self, notification_id: NotificationId, *, sent_at: datetime) -> None: ...

    def mark_failed(
        self,
        notification_id: NotificationId,
        *,
        error: str,
        max_attempts: int,
        now: datetime,
    ) -> None:
        """Record a failed delivery attempt.

        Increments ``attempts`` and sets ``last_error``; transitions to
        ``FAILED`` once ``attempts >= max_attempts``, otherwise stays
        ``PENDING`` for the next scheduled dispatcher run to retry.
        """
        ...


class SearchExecutionRepository(Protocol):
    """Audit trail of scrape attempts — one row per attempt, success or failure."""

    def record(
        self,
        *,
        portal_slug: str,
        query_signature: str,
        status: SearchExecutionStatus,
        listings_found: int,
        listings_new: int,
        normalization_issues: int,
        error: str | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> None: ...

    def list_recent(self, limit: int) -> Sequence[SearchExecution]:
        """Most recent scrape attempts across every portal, newest first —
        the data source for the dashboard's execution-health view (doc05 §6).
        """
        ...


class SearchCacheRepository(Protocol):
    """TTL-based cache of a query signature's resulting property ids (doc06 §4)."""

    def get(self, signature: str, *, now: datetime) -> Sequence[PropertyId] | None:
        """Return cached property ids, or ``None`` on a miss or expiry."""
        ...

    def put(
        self,
        signature: str,
        portal_slug: str,
        property_ids: Sequence[PropertyId],
        *,
        fetched_at: datetime,
        ttl_seconds: int,
    ) -> None: ...
