"""Contract tests: a minimal in-memory implementation satisfies the ports."""

from __future__ import annotations

from types import TracebackType

from real_estate.domain.model import AlertId, PropertyId, SearchAlert, UserId
from real_estate.domain.model.property import Property
from real_estate.domain.ports import (
    NotificationMessage,
    PortalQuery,
    RawListing,
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


class _InMemoryUoW:
    def __init__(self) -> None:
        self.alerts = _InMemoryAlertRepo()
        self.properties = _InMemoryPropertyRepo()
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
