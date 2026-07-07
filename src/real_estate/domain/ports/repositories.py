"""Repository ports.

The domain speaks in collections of aggregates, not SQL. Infrastructure
provides concrete adapters (e.g. ``SqlAlchemyAlertRepository``). Repositories
are always scoped by ``user_id`` where the entity is user-owned (multi-tenant,
driver D5) — enforced by the adapters.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import AlertId, PropertyId, UserId
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.property import Property


class AlertRepository(Protocol):
    """Persistence of the :class:`SearchAlert` aggregate."""

    def add(self, alert: SearchAlert) -> None: ...

    def get(self, alert_id: AlertId) -> SearchAlert | None: ...

    def list_for_user(self, user_id: UserId) -> Sequence[SearchAlert]: ...


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

    def add_if_new(self, match: AlertMatch) -> bool:
        """Persist ``match`` if it doesn't already exist; return whether it was new."""
        ...


class PortalListingRepository(Protocol):
    """Tracks the raw, per-portal record backing a canonical :class:`Property`.

    ``get_content_hash`` lets a use-case skip re-normalizing a listing that
    hasn't changed since the last scrape (doc03, doc05 §2).
    """

    def get_content_hash(self, portal_slug: str, external_id: str) -> str | None: ...

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


class SearchExecutionStatus(StrEnum):
    """Outcome of one scrape attempt for one query signature (doc03)."""

    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


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
        error: str | None,
        started_at: datetime,
        finished_at: datetime,
    ) -> None: ...


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
