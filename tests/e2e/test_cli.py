"""e2e: the Typer CLI against a real (temp) SQLite DB — only the scraper and
notifier are faked (no real network), matching issue #34's acceptance
criteria: create/list alerts, list recent matches, manage channels, trigger
a cycle, all delegating to real application use-cases.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import typer
from typer.testing import CliRunner

from real_estate.application.ports import Clock, PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.application.use_cases.dispatch_notifications import DispatchNotifications
from real_estate.application.use_cases.list_alerts import ListAlerts
from real_estate.application.use_cases.list_channels import ListChannels
from real_estate.application.use_cases.list_matches import ListMatches
from real_estate.application.use_cases.planner_tick import PlannerTick
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.domain.ports.notifier import NotificationMessage
from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.domain.rules import SpecificationFactory
from real_estate.domain.rules import default_registry as default_field_registry
from real_estate.domain.services.alert_engine import AlertEngine
from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer
from real_estate.presentation.cli.app import CliContext, build_cli_app

NOW = datetime(2026, 7, 10, 12, 0)

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

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        return self._listings


class _FakeNotifier:
    channel_type = "TELEGRAM"

    def __init__(self) -> None:
        self.sent: list[tuple[str, NotificationMessage]] = []

    def send(self, target: str, message: NotificationMessage) -> None:
        self.sent.append((target, message))


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


def _build_cli(
    persistence, *, scraper: _FakeScraper, notifier: _FakeNotifier, clock: Clock
) -> typer.Typer:
    field_registry = default_field_registry()
    engine = AlertEngine(SpecificationFactory(field_registry))
    planner = SearchPlanner({"idealista": _CAPABILITIES})
    run_alert_cycle = RunAlertCycle(
        uow_factory=persistence.new_uow,
        planner=planner,
        scraper_for_portal=lambda _slug: scraper,
        normalizer_for_portal=lambda _slug: IdealistaNormalizer(),
        engine=engine,
        clock=clock,
    )
    planner_tick = PlannerTick(
        uow_factory=persistence.new_uow, run_alert_cycle=run_alert_cycle, clock=clock
    )
    dispatch_notifications = DispatchNotifications(
        uow_factory=persistence.new_uow,
        notifier_for_channel_type=lambda _channel_type: notifier,
        rate_limit=lambda _channel_type: None,
        clock=clock,
    )
    ctx = CliContext(
        user_id=lambda: persistence.user_id,
        create_alert=CreateAlert(
            uow_factory=persistence.new_uow, field_registry=field_registry, clock=clock
        ),
        list_alerts=ListAlerts(uow_factory=persistence.new_uow),
        list_matches=ListMatches(uow_factory=persistence.new_uow),
        create_channel=CreateChannel(uow_factory=persistence.new_uow),
        list_channels=ListChannels(uow_factory=persistence.new_uow),
        planner_tick=planner_tick,
        dispatch_notifications=dispatch_notifications,
        run_scheduler_forever=lambda: None,
    )
    return build_cli_app(ctx)


def test_help_never_resolves_user_id(persistence) -> None:
    """--help must not touch the DB (ensure_default_user) just to print
    usage — Typer/Click short-circuits before a command body runs, so a lazy
    ``user_id`` callable should never actually be called here."""

    def poison() -> None:
        raise AssertionError("user_id was resolved just to print --help")

    runner = CliRunner()
    field_registry = default_field_registry()
    ctx = CliContext(
        user_id=poison,  # type: ignore[arg-type]
        create_alert=CreateAlert(
            uow_factory=persistence.new_uow, field_registry=field_registry, clock=_FixedClock(NOW)
        ),
        list_alerts=ListAlerts(uow_factory=persistence.new_uow),
        list_matches=ListMatches(uow_factory=persistence.new_uow),
        create_channel=CreateChannel(uow_factory=persistence.new_uow),
        list_channels=ListChannels(uow_factory=persistence.new_uow),
        planner_tick=None,  # type: ignore[arg-type]
        dispatch_notifications=None,  # type: ignore[arg-type]
        run_scheduler_forever=lambda: None,
    )
    poisoned_app = build_cli_app(ctx)

    result = runner.invoke(poisoned_app, ["--help"])
    assert result.exit_code == 0

    result = runner.invoke(poisoned_app, ["alerts", "create", "--help"])
    assert result.exit_code == 0


def test_alerts_create_then_list(persistence) -> None:
    app = _build_cli(
        persistence, scraper=_FakeScraper(), notifier=_FakeNotifier(), clock=_FixedClock(NOW)
    )
    runner = CliRunner()

    create_result = runner.invoke(
        app,
        [
            "alerts",
            "create",
            "Land in Pontevedra",
            "--province",
            "36",
            "--property-type",
            "LAND",
        ],
    )
    assert create_result.exit_code == 0
    assert "Created alert" in create_result.stdout

    list_result = runner.invoke(app, ["alerts", "list"])
    assert list_result.exit_code == 0
    assert "Land in Pontevedra" in list_result.stdout


def test_channels_create_then_list(persistence) -> None:
    app = _build_cli(
        persistence, scraper=_FakeScraper(), notifier=_FakeNotifier(), clock=_FixedClock(NOW)
    )
    runner = CliRunner()

    create_result = runner.invoke(app, ["channels", "create", "--target", "chat-42"])
    assert create_result.exit_code == 0
    assert "Created channel" in create_result.stdout

    list_result = runner.invoke(app, ["channels", "list"])
    assert list_result.exit_code == 0
    assert "chat-42" in list_result.stdout
    assert "TELEGRAM" in list_result.stdout


def test_run_cycle_scrapes_and_reports_a_match(persistence) -> None:
    scraper = _FakeScraper([_matching_raw_listing()])
    app = _build_cli(persistence, scraper=scraper, notifier=_FakeNotifier(), clock=_FixedClock(NOW))
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "alerts",
            "create",
            "Land in Pontevedra",
            "--province",
            "36",
            "--property-type",
            "LAND",
        ],
    )

    result = runner.invoke(app, ["run-cycle"])

    assert result.exit_code == 0
    assert "matches created: 1" in result.stdout


def test_list_matches_and_dispatch_after_a_cycle(persistence) -> None:
    scraper = _FakeScraper([_matching_raw_listing()])
    notifier = _FakeNotifier()
    app = _build_cli(persistence, scraper=scraper, notifier=notifier, clock=_FixedClock(NOW))
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "alerts",
            "create",
            "Land in Pontevedra",
            "--province",
            "36",
            "--property-type",
            "LAND",
        ],
    )
    runner.invoke(app, ["channels", "create", "--target", "chat-42"])

    cycle_result = runner.invoke(app, ["run-cycle"])
    assert "matches created: 1" in cycle_result.stdout

    matches_result = runner.invoke(app, ["list-matches"])
    assert matches_result.exit_code == 0
    assert "Finca con agua" in matches_result.stdout
    assert "idealista.com" in matches_result.stdout

    dispatch_result = runner.invoke(app, ["dispatch"])
    assert dispatch_result.exit_code == 0
    assert "1 sent" in dispatch_result.stdout
    assert len(notifier.sent) == 1
