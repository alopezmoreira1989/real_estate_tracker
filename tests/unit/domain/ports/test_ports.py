"""Contract tests: a minimal in-memory implementation satisfies the ports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from types import TracebackType
from typing import Any

from real_estate.domain.model import AlertId, PropertyId, SearchAlert, UserId
from real_estate.domain.model.match import AlertMatch
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
        self._keys: set[tuple[AlertId, PropertyId]] = set()

    def add_if_new(self, match: AlertMatch) -> bool:
        key = (match.alert_id, match.property_id)
        if key in self._keys:
            return False
        self._keys.add(key)
        return True


class _InMemoryPortalListingRepo:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], tuple[PropertyId, str]] = {}

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


class _InMemoryUoW:
    def __init__(self) -> None:
        self.alerts = _InMemoryAlertRepo()
        self.properties = _InMemoryPropertyRepo()
        self.matches = _InMemoryMatchRepo()
        self.portal_listings = _InMemoryPortalListingRepo()
        self.search_cache = _InMemorySearchCacheRepo()
        self.search_executions = _InMemorySearchExecutionRepo()
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
