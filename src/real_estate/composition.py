"""Composition root: the only module allowed to import every concrete adapter and wire them
(via dependency injection) into the use-cases that the presentation layer calls.
"""

from __future__ import annotations

import time

import typer

from real_estate.application.ports import PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.application.use_cases.dispatch_notifications import DispatchNotifications
from real_estate.application.use_cases.list_alerts import ListAlerts
from real_estate.application.use_cases.list_channels import ListChannels
from real_estate.application.use_cases.list_matches import ListMatches
from real_estate.application.use_cases.planner_tick import PlannerTick
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.ports import Notifier, UnitOfWork
from real_estate.domain.rules import SpecificationFactory
from real_estate.domain.rules import default_registry as default_field_registry
from real_estate.domain.services.alert_engine import AlertEngine
from real_estate.infrastructure.clock import SystemClock
from real_estate.infrastructure.config.portal_capabilities import PORTAL_CAPABILITIES
from real_estate.infrastructure.config.settings import Settings
from real_estate.infrastructure.logging import configure_logging
from real_estate.infrastructure.normalizers import default_registry as default_normalizer_registry
from real_estate.infrastructure.notifications.telegram_notifier import TelegramNotifier
from real_estate.infrastructure.persistence.bootstrap import ensure_default_user
from real_estate.infrastructure.persistence.database import create_db_engine, create_session_factory
from real_estate.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from real_estate.infrastructure.scheduling.scheduler import build_scheduler
from real_estate.infrastructure.scrapers import default_registry as default_scraper_registry
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter
from real_estate.presentation.cli.app import CliContext, build_cli_app

_DEFAULT_PORTAL_CAPABILITIES = PortalCapabilities(
    portal_slug="",
    pushable_fields=frozenset(),
    rate_limit_per_second=1.0,
    circuit_breaker_failure_threshold=5,
    circuit_breaker_cooldown_seconds=60.0,
)
_TELEGRAM_MESSAGES_PER_SECOND = 1.0


def build_app() -> typer.Typer:
    """Wire every adapter and use-case, and return the runnable Typer app."""
    settings = Settings()
    configure_logging(settings.environment, settings.log_level)

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def resolve_user_id() -> UserId:
        # Lazy: only actual commands need the DB (Typer/Click's --help
        # short-circuits before a command body runs, but this whole function
        # runs before Typer parses argv, so an eager call here would touch
        # the DB unconditionally on every invocation, including --help).
        return ensure_default_user(session_factory, settings.owner_email)

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory, encryption_key=settings.notification_encryption_key
        )

    clock = SystemClock()
    scraper_registry = default_scraper_registry()
    normalizer_registry = default_normalizer_registry()
    planner = SearchPlanner(PORTAL_CAPABILITIES)
    field_registry = default_field_registry()
    alert_engine = AlertEngine(SpecificationFactory(field_registry))

    def max_concurrency_for_portal(portal_slug: str) -> int:
        return PORTAL_CAPABILITIES.get(portal_slug, _DEFAULT_PORTAL_CAPABILITIES).max_concurrency

    run_alert_cycle = RunAlertCycle(
        uow_factory=uow_factory,
        planner=planner,
        scraper_for_portal=scraper_registry.for_portal,
        normalizer_for_portal=normalizer_registry.for_portal,
        engine=alert_engine,
        clock=clock,
        max_concurrency_for_portal=max_concurrency_for_portal,
    )
    planner_tick = PlannerTick(
        uow_factory=uow_factory, run_alert_cycle=run_alert_cycle, clock=clock
    )

    notifiers: dict[str, Notifier] = {
        "TELEGRAM": TelegramNotifier(settings.telegram_bot_token or ""),
    }
    rate_limiters = {"TELEGRAM": TokenBucketRateLimiter(_TELEGRAM_MESSAGES_PER_SECOND)}
    dispatch_notifications = DispatchNotifications(
        uow_factory=uow_factory,
        notifier_for_channel_type=lambda channel_type: notifiers[channel_type],
        rate_limit=lambda channel_type: rate_limiters[channel_type].acquire(),
        clock=clock,
    )

    create_alert = CreateAlert(uow_factory=uow_factory, field_registry=field_registry, clock=clock)
    create_channel = CreateChannel(uow_factory=uow_factory)
    list_alerts = ListAlerts(uow_factory=uow_factory)
    list_matches = ListMatches(uow_factory=uow_factory)
    list_channels = ListChannels(uow_factory=uow_factory)

    scheduler = build_scheduler(
        planner_tick=planner_tick.run,
        dispatch_notifications=dispatch_notifications.run,
        planner_interval_seconds=settings.planner_interval_seconds,
        planner_jitter_seconds=settings.planner_jitter_seconds,
        dispatcher_interval_seconds=settings.dispatcher_interval_seconds,
    )

    def run_scheduler_forever() -> None:
        scheduler.start()
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

    cli_context = CliContext(
        user_id=resolve_user_id,
        create_alert=create_alert,
        list_alerts=list_alerts,
        list_matches=list_matches,
        create_channel=create_channel,
        list_channels=list_channels,
        planner_tick=planner_tick,
        dispatch_notifications=dispatch_notifications,
        run_scheduler_forever=run_scheduler_forever,
    )
    return build_cli_app(cli_context)
