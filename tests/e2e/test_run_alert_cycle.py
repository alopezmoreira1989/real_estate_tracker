"""e2e: RunAlertCycle against a real (temp) SQLite DB, the real Rule Engine,
and the real IdealistaNormalizer — only the Scraper is faked (no real
network), matching issue #28's acceptance criteria directly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.application.ports import Clock, PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    ChannelType,
    GroupOperator,
    NotificationChannel,
    NotificationChannelId,
    Operator,
    RuleGroup,
    SearchAlert,
    UserId,
)
from real_estate.domain.ports.scraper import PortalQuery, RawListing, ScraperError
from real_estate.domain.rules import SpecificationFactory
from real_estate.domain.rules import default_registry as default_field_registry
from real_estate.domain.services.alert_engine import AlertEngine
from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer

NOW = datetime(2026, 7, 4, 12, 0)  # naive: SQLite does not persist tz

_CAPABILITIES = PortalCapabilities(
    portal_slug="idealista",
    pushable_fields=frozenset({"province", "property_type", "listing_type", "price"}),
    rate_limit_per_second=1.0,
    circuit_breaker_failure_threshold=5,
    circuit_breaker_cooldown_seconds=60.0,
)


@dataclass
class _FixedClock:
    _now: datetime

    def now(self) -> datetime:
        return self._now


class _FakeScraper:
    """Stands in for a real HTTP scraper — returns canned RawListings, or
    raises to exercise failure isolation. Counts calls to prove caching
    actually skips a re-scrape."""

    portal_slug = "idealista"

    def __init__(
        self, listings: Sequence[RawListing] = (), *, error: Exception | None = None
    ) -> None:
        self._listings = listings
        self._error = error
        self.calls = 0

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._listings


def _land_alert(user_id: UserId, *, price_per_m2_lte: str = "20") -> SearchAlert:
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("property_type", Operator.EQ, "LAND"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal(price_per_m2_lte)),
        ),
    )
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=user_id,
        name="Land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=conditions,
        now=NOW,
    )


def _matching_raw_listing(external_id: str = "1") -> RawListing:
    return RawListing(
        portal_slug="idealista",
        external_id=external_id,
        url=f"https://idealista.com/inmueble/{external_id}/",
        scraped_at=NOW,
        raw={
            "precio": "60.000 €",
            "superficie": "3.000 m²",
            "tipo": "Suelo",
            "operacion": "Venta",
            "provincia": "Pontevedra",
            "titulo": "Finca con agua",
            "descripcion": "Suelo urbanizable con acceso a agua",
        },
    )


def _make_cycle(persistence, scraper: _FakeScraper, *, clock: Clock | None = None) -> RunAlertCycle:
    engine = AlertEngine(SpecificationFactory(default_field_registry()))
    planner = SearchPlanner({"idealista": _CAPABILITIES})
    return RunAlertCycle(
        uow_factory=persistence.new_uow,
        planner=planner,
        scraper_for_portal=lambda _slug: scraper,
        normalizer_for_portal=lambda _slug: IdealistaNormalizer(),
        engine=engine,
        clock=clock or _FixedClock(NOW),
        cache_ttl_seconds=900,
    )


def test_cycle_scrapes_normalizes_and_creates_a_match(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    cycle = _make_cycle(persistence, scraper)

    report = cycle.run([alert])

    assert report.queries_planned == 1
    assert report.queries_succeeded == 1
    assert report.queries_failed == 0
    assert report.matches_created == 1
    assert scraper.calls == 1

    with persistence.new_uow() as uow:
        reloaded = uow.alerts.get(alert.id)
    assert reloaded is not None
    assert reloaded.last_run_at == NOW


def test_cycle_is_idempotent_and_caches_within_ttl(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    cycle = _make_cycle(persistence, scraper)

    first = cycle.run([alert])
    second = cycle.run([alert])

    assert first.matches_created == 1
    assert second.matches_created == 0  # already matched — idempotent, no duplicate
    assert scraper.calls == 1  # second run hit the search cache, no re-scrape


def test_non_matching_listing_is_ingested_but_creates_no_match(persistence) -> None:
    alert = _land_alert(persistence.user_id, price_per_m2_lte="5")  # too strict to match
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])  # price_per_m2 = 20
    cycle = _make_cycle(persistence, scraper)

    report = cycle.run([alert])

    assert report.queries_succeeded == 1
    assert report.matches_created == 0


def test_scraper_failure_is_isolated_and_the_cycle_continues(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper(error=ScraperError("portal unreachable"))
    cycle = _make_cycle(persistence, scraper)

    report = cycle.run([alert])  # must not raise — the failure is isolated (D7, doc08 §4)

    assert report.queries_failed == 1
    assert report.queries_succeeded == 0
    assert report.matches_created == 0


def test_a_new_match_enqueues_a_pending_notification_per_enabled_channel(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    channel = NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=persistence.user_id,
        channel_type=ChannelType.TELEGRAM,
        target="chat-1",
    )
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.notification_channels.add(channel)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    cycle = _make_cycle(persistence, scraper)

    report = cycle.run([alert])

    assert report.matches_created == 1
    with persistence.new_uow() as uow:
        pending = uow.notifications.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].channel_id == channel.id


def test_ten_alerts_on_the_same_search_scrape_idealista_once(persistence) -> None:
    alerts = [_land_alert(persistence.user_id) for _ in range(10)]
    with persistence.new_uow() as uow:
        for alert in alerts:
            uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    cycle = _make_cycle(persistence, scraper)

    report = cycle.run(alerts)

    assert scraper.calls == 1  # one scrape, fanned out to all ten alerts (D3)
    assert report.matches_created == 10
