"""Contract tests: a minimal in-memory implementation satisfies the ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from types import TracebackType
from typing import Any
from uuid import uuid4

from real_estate.domain.model import AlertId, PropertyId, SearchAlert, UserId
from real_estate.domain.model.identifiers import MatchId, NotificationChannelId, NotificationId
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.notification import Notification, NotificationStatus
from real_estate.domain.model.notification_channel import NotificationChannel
from real_estate.domain.model.property import Property
from real_estate.domain.ports import (
    NormalizationIssue,
    NormalizationResult,
    NotificationMessage,
    PortalQuery,
    RawListing,
    SearchExecutionStatus,
    UnitOfWork,
)


class _InMemoryAlertRepo:
    def __init__(self) -> None:
        self._by_id: dict[AlertId, SearchAlert] = {}

    def add(self, alert: SearchAlert) -> None:
        self._by_id[alert.id] = alert

    def get(self, alert_id: AlertId) -> SearchAlert | None:
        return self._by_id.get(alert_id)

    def list_for_user(self, user_id: UserId) -> list[SearchAlert]:
        return [a for a in self._by_id.values() if a.user_id == user_id]


class _InMemoryPropertyRepo:
    def __init__(self) -> None:
        self._by_id: dict[PropertyId, Property] = {}

    def add(self, prop: Property) -> None:
        self._by_id[prop.id] = prop

    def get(self, property_id: PropertyId) -> Property | None:
        return self._by_id.get(property_id)


class _InMemoryMatchRepo:
    def __init__(self) -> None:
        self._by_key: dict[tuple[AlertId, PropertyId], AlertMatch] = {}

    def add_if_new(self, match: AlertMatch) -> MatchId | None:
        key = (match.alert_id, match.property_id)
        if key in self._by_key:
            return None
        stored = AlertMatch(
            alert_id=match.alert_id,
            property_id=match.property_id,
            matched_at=match.matched_at,
            status=match.status,
            id=MatchId(uuid4()),
        )
        self._by_key[key] = stored
        assert stored.id is not None
        return stored.id

    def get(self, match_id: MatchId) -> AlertMatch | None:
        for match in self._by_key.values():
            if match.id == match_id:
                return match
        return None


class _InMemoryPortalListingRepo:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], tuple[PropertyId, str]] = {}
        self._urls: dict[PropertyId, str] = {}

    def find_unchanged_property_id(
        self, portal_slug: str, external_id: str, content_hash: str
    ) -> PropertyId | None:
        record = self._records.get((portal_slug, external_id))
        if record is not None and record[1] == content_hash:
            return record[0]
        return None

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
    ) -> None:
        self._records[(portal_slug, external_id)] = (property_id, content_hash)
        self._urls[property_id] = url

    def get_url_for_property(self, property_id: PropertyId) -> str | None:
        return self._urls.get(property_id)


class _InMemorySearchCacheRepo:
    def __init__(self) -> None:
        self._entries: dict[str, Sequence[PropertyId]] = {}

    def get(self, signature: str, *, now: datetime) -> Sequence[PropertyId] | None:
        return self._entries.get(signature)

    def put(
        self,
        signature: str,
        portal_slug: str,
        property_ids: Sequence[PropertyId],
        *,
        fetched_at: datetime,
        ttl_seconds: int,
    ) -> None:
        self._entries[signature] = property_ids


class _InMemorySearchExecutionRepo:
    def __init__(self) -> None:
        self.records: list[SearchExecutionStatus] = []

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
    ) -> None:
        self.records.append(status)


class _InMemoryNotificationChannelRepo:
    def __init__(self) -> None:
        self._by_id: dict[NotificationChannelId, NotificationChannel] = {}

    def add(self, channel: NotificationChannel) -> None:
        self._by_id[channel.id] = channel

    def get(self, channel_id: NotificationChannelId) -> NotificationChannel | None:
        return self._by_id.get(channel_id)

    def list_enabled_for_user(self, user_id: UserId) -> list[NotificationChannel]:
        return [c for c in self._by_id.values() if c.user_id == user_id and c.is_enabled]


class _InMemoryNotificationRepo:
    def __init__(self) -> None:
        self._by_id: dict[NotificationId, Notification] = {}

    def enqueue(
        self, match_id: MatchId, channel_id: NotificationChannelId, *, now: datetime
    ) -> bool:
        key_exists = any(
            n.match_id == match_id and n.channel_id == channel_id for n in self._by_id.values()
        )
        if key_exists:
            return False
        notification_id = NotificationId(uuid4())
        self._by_id[notification_id] = Notification(
            match_id=match_id, channel_id=channel_id, created_at=now, id=notification_id
        )
        return True

    def list_pending(self, limit: int) -> list[Notification]:
        return [n for n in self._by_id.values() if n.status == NotificationStatus.PENDING][:limit]

    def mark_sent(self, notification_id: NotificationId, *, sent_at: datetime) -> None:
        pass

    def mark_failed(
        self, notification_id: NotificationId, *, error: str, max_attempts: int, now: datetime
    ) -> None:
        pass


class _InMemoryUoW:
    def __init__(self) -> None:
        self.alerts = _InMemoryAlertRepo()
        self.properties = _InMemoryPropertyRepo()
        self.matches = _InMemoryMatchRepo()
        self.portal_listings = _InMemoryPortalListingRepo()
        self.search_cache = _InMemorySearchCacheRepo()
        self.search_executions = _InMemorySearchExecutionRepo()
        self.notification_channels = _InMemoryNotificationChannelRepo()
        self.notifications = _InMemoryNotificationRepo()
        self.committed = False

    def __enter__(self) -> _InMemoryUoW:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


def test_in_memory_uow_satisfies_the_protocol() -> None:
    uow = _InMemoryUoW()
    assert isinstance(uow, UnitOfWork)


def test_uow_exposes_working_repositories() -> None:
    uow = _InMemoryUoW()
    with uow:
        uow.commit()
    assert uow.committed is True


def test_boundary_dtos_construct() -> None:
    q = PortalQuery(portal_slug="idealista", params={"province": "36"})
    assert q.params["province"] == "36"

    from datetime import UTC, datetime

    raw = RawListing(
        portal_slug="idealista",
        external_id="abc123",
        url="https://idealista.com/abc123",
        scraped_at=datetime(2026, 7, 4, tzinfo=UTC),
        raw={"precio": "120.000 €"},
    )
    assert raw.raw["precio"] == "120.000 €"

    msg = NotificationMessage(title="New match", body="A plot in Pontevedra", url="https://x")
    assert msg.title == "New match"


def test_normalization_result_carries_property_and_issues() -> None:
    issue = NormalizationIssue(
        field="land_type", message="unmapped vocabulary", raw_value="parcela"
    )
    result = NormalizationResult(property=None, issues=(issue,))

    assert result.property is None
    assert result.issues[0].raw_value == "parcela"


def test_normalization_result_defaults_to_no_issues() -> None:
    result = NormalizationResult(property=None)

    assert result.issues == ()
