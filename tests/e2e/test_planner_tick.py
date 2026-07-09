"""e2e: PlannerTick against a real (temp) SQLite DB — proves the due-set
selection (doc06 §5) actually gates which alerts RunAlertCycle sees.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from real_estate.application.ports import Clock, PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.application.use_cases.planner_tick import PlannerTick
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    GroupOperator,
    Operator,
    RuleGroup,
    SearchAlert,
    UserId,
)
from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.domain.rules import SpecificationFactory
from real_estate.domain.rules import default_registry as default_field_registry
from real_estate.domain.services.alert_engine import AlertEngine
from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer

NOW = datetime(2026, 7, 9, 12, 0)

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
    portal_slug = "idealista"

    def __init__(self, listings: Sequence[RawListing] = ()) -> None:
        self._listings = listings
        self.calls = 0

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        self.calls += 1
        return self._listings


def _land_alert(user_id: UserId) -> SearchAlert:
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("property_type", Operator.EQ, "LAND"),
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


def _matching_raw_listing() -> RawListing:
    return RawListing(
        portal_slug="idealista",
        external_id="1",
        url="https://idealista.com/inmueble/1/",
        scraped_at=NOW,
        raw={
            "precio": "60.000 €",
            "superficie": "3.000 m²",
            "tipo": "Suelo",
            "operacion": "Venta",
            "provincia": "Pontevedra",
            "titulo": "Finca con agua",
            "descripcion": "Suelo urbanizable",
        },
    )


def _make_tick(persistence, scraper: _FakeScraper, *, clock: Clock) -> PlannerTick:
    engine = AlertEngine(SpecificationFactory(default_field_registry()))
    planner = SearchPlanner({"idealista": _CAPABILITIES})
    run_alert_cycle = RunAlertCycle(
        uow_factory=persistence.new_uow,
        planner=planner,
        scraper_for_portal=lambda _slug: scraper,
        normalizer_for_portal=lambda _slug: IdealistaNormalizer(),
        engine=engine,
        clock=clock,
    )
    return PlannerTick(
        uow_factory=persistence.new_uow, run_alert_cycle=run_alert_cycle, clock=clock
    )


def test_a_never_run_alert_is_picked_up_and_produces_a_match(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    tick = _make_tick(persistence, scraper, clock=_FixedClock(NOW))

    report = tick.run()

    assert report.queries_planned == 1
    assert report.matches_created == 1
    assert scraper.calls == 1


def test_a_recently_run_alert_is_not_due_and_is_skipped(persistence) -> None:
    alert = _land_alert(persistence.user_id)
    alert.mark_run(now=NOW)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    tick = _make_tick(persistence, scraper, clock=_FixedClock(NOW + timedelta(seconds=1)))

    report = tick.run()

    assert report.queries_planned == 0
    assert scraper.calls == 0


def test_an_alert_becomes_due_again_once_its_frequency_elapses(persistence) -> None:
    alert = _land_alert(persistence.user_id)  # frequency_seconds=900
    alert.mark_run(now=NOW)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    scraper = _FakeScraper([_matching_raw_listing()])
    tick = _make_tick(persistence, scraper, clock=_FixedClock(NOW + timedelta(seconds=901)))

    report = tick.run()

    assert report.queries_planned == 1
    assert report.matches_created == 1
