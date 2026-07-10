"""Composition root: the only module allowed to import every concrete adapter and wire them
(via dependency injection) into the use-cases the presentation layer calls.

``build_dependencies()`` does all the wiring once, framework-agnostic; both presentation surfaces
consume the exact same use-case instances from it — literally "runs against the same application
layer" (issue #35). Each presentation surface defines its own context type (``CliContext`` in
``presentation/cli/app.py``, ``DashboardContext`` in ``presentation/web/app.py``) and *this* module
builds and injects it — never the reverse, so neither presentation module ever imports
``real_estate.composition`` or (transitively) ``real_estate.infrastructure``:

- ``build_app()`` returns the runnable Typer app.
- ``run_dashboard()`` is what ``dashboard.py`` (Streamlit's actual entry point — its execution
  model requires a literal runnable script, unlike Typer) calls.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import typer

from real_estate.application.ports import PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.application.use_cases.dispatch_notifications import DispatchNotifications
from real_estate.application.use_cases.list_alerts import ListAlerts
from real_estate.application.use_cases.list_channels import ListChannels
from real_estate.application.use_cases.list_matches import ListMatches
from real_estate.application.use_cases.list_search_executions import ListSearchExecutions
from real_estate.application.use_cases.planner_tick import PlannerTick
from real_estate.application.use_cases.run_alert_cycle import RunAlertCycle
from real_estate.application.use_cases.update_alert import UpdateAlert
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.ports import Notifier, UnitOfWork
from real_estate.domain.rules import FieldRegistry, SpecificationFactory
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


@dataclass(frozen=True, slots=True)
class Dependencies:
    """Every use-case + shared dependency a presentation surface might need."""

    user_id: Callable[[], UserId]
    field_registry: FieldRegistry
    create_alert: CreateAlert
    update_alert: UpdateAlert
    list_alerts: ListAlerts
    list_matches: ListMatches
    create_channel: CreateChannel
    list_channels: ListChannels
    list_search_executions: ListSearchExecutions
    planner_tick: PlannerTick
    dispatch_notifications: DispatchNotifications
    run_scheduler_forever: Callable[[], None]


def build_dependencies() -> Dependencies:
    """Wire every adapter and use-case. The one place both presentation surfaces share."""
    settings = Settings()
    configure_logging(settings.environment, settings.log_level)

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def resolve_user_id() -> UserId:
        # Lazy: resolving touches the DB (ensure_default_user); callers decide when that's
        # appropriate (e.g. the CLI must not do it just to print --help).
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

    return Dependencies(
        user_id=resolve_user_id,
        field_registry=field_registry,
        create_alert=CreateAlert(
            uow_factory=uow_factory, field_registry=field_registry, clock=clock
        ),
        update_alert=UpdateAlert(
            uow_factory=uow_factory, field_registry=field_registry, clock=clock
        ),
        list_alerts=ListAlerts(uow_factory=uow_factory),
        list_matches=ListMatches(uow_factory=uow_factory),
        create_channel=CreateChannel(uow_factory=uow_factory),
        list_channels=ListChannels(uow_factory=uow_factory),
        list_search_executions=ListSearchExecutions(uow_factory=uow_factory),
        planner_tick=planner_tick,
        dispatch_notifications=dispatch_notifications,
        run_scheduler_forever=run_scheduler_forever,
    )


def build_app() -> typer.Typer:
    """Wire everything and return the runnable Typer app (the CLI's entry point)."""
    deps = build_dependencies()
    cli_context = CliContext(
        user_id=deps.user_id,
        create_alert=deps.create_alert,
        list_alerts=deps.list_alerts,
        list_matches=deps.list_matches,
        create_channel=deps.create_channel,
        list_channels=deps.list_channels,
        planner_tick=deps.planner_tick,
        dispatch_notifications=deps.dispatch_notifications,
        run_scheduler_forever=deps.run_scheduler_forever,
    )
    return build_cli_app(cli_context)


def run_dashboard() -> None:
    """Wire everything and render the Streamlit dashboard (dashboard.py's entry point).

    Streamlit is imported locally, not at module level, so the CLI's startup path never pays for
    it — ``composition.py`` is shared by both entry points.
    """
    import streamlit as st

    from real_estate.presentation.web.app import DashboardContext, render

    @st.cache_resource
    def _cached_dependencies() -> Dependencies:
        return build_dependencies()

    deps = _cached_dependencies()
    dashboard_context = DashboardContext(
        user_id=deps.user_id,
        create_alert=deps.create_alert,
        update_alert=deps.update_alert,
        list_alerts=deps.list_alerts,
        list_matches=deps.list_matches,
        create_channel=deps.create_channel,
        list_channels=deps.list_channels,
        list_search_executions=deps.list_search_executions,
    )
    render(dashboard_context)
