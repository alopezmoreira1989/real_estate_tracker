"""Typer CLI — operates the platform: manage alerts/channels, list recent
matches, trigger a cycle, run the scheduler unattended (doc07).

Thin: each command parses input and calls exactly one application use-case.
``composition.py`` builds every use-case and the :class:`CliContext` this
module receives (Dependency Injection) — presentation never imports
infrastructure directly (CLAUDE.md §6); ``run_scheduler_forever`` is an
injected callable rather than a concrete APScheduler type for the same
reason.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import typer

from real_estate.application.dto import DispatchReport, MatchView, RunAlertCycleReport
from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.application.use_cases.dispatch_notifications import DispatchNotifications
from real_estate.application.use_cases.list_alerts import ListAlerts
from real_estate.application.use_cases.list_channels import ListChannels
from real_estate.application.use_cases.list_matches import ListMatches
from real_estate.application.use_cases.planner_tick import PlannerTick
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.model.notification_channel import ChannelType


@dataclass(frozen=True, slots=True)
class CliContext:
    """Every dependency the CLI needs, built once by composition.py.

    ``user_id`` is a callable, not a resolved value: resolving it touches the
    DB (``ensure_default_user``), which must not happen just to print
    ``--help`` — Typer/Click short-circuits before a command body runs, but
    composition.py builds this context before Typer even parses argv, so an
    eager DB call here would run unconditionally on every invocation.
    """

    user_id: Callable[[], UserId]
    create_alert: CreateAlert
    list_alerts: ListAlerts
    list_matches: ListMatches
    create_channel: CreateChannel
    list_channels: ListChannels
    planner_tick: PlannerTick
    dispatch_notifications: DispatchNotifications
    run_scheduler_forever: Callable[[], None]


def build_cli_app(ctx: CliContext) -> typer.Typer:
    """Build the Typer app, wiring each command to one use-case in ``ctx``."""
    app = typer.Typer(help="Real Estate Alert Platform — operational CLI.")
    alerts_app = typer.Typer(help="Manage saved alerts.")
    channels_app = typer.Typer(help="Manage notification channels.")
    app.add_typer(alerts_app, name="alerts")
    app.add_typer(channels_app, name="channels")

    @alerts_app.command("create")
    def alerts_create(
        name: str,
        province: str = typer.Option(..., help="INE province code, e.g. 36"),
        property_type: str = typer.Option(..., help="LAND, FLAT, HOUSE, ..."),
        listing_type: str = typer.Option("SALE", help="SALE or RENT"),
        frequency_seconds: int = typer.Option(900, help="Minimum re-check interval, in seconds"),
        condition: list[str] = typer.Option(
            [],
            "--condition",
            help="Extra AND-only condition FIELD:OPERATOR[:VALUE] (ADR-014), repeatable",
        ),
    ) -> None:
        alert = ctx.create_alert.run(
            user_id=ctx.user_id(),
            name=name,
            portal_slugs=frozenset({"idealista"}),
            frequency_seconds=frequency_seconds,
            condition_strings=[
                f"province:EQ:{province}",
                f"property_type:EQ:{property_type}",
                f"listing_type:EQ:{listing_type}",
                *condition,
            ],
        )
        typer.echo(f"Created alert {alert.id} ({alert.name!r})")

    @alerts_app.command("list")
    def alerts_list() -> None:
        for alert in ctx.list_alerts.run(user_id=ctx.user_id()):
            status = "active" if alert.is_active else "inactive"
            typer.echo(f"{alert.id}  {alert.name!r}  [{status}]  every {alert.frequency_seconds}s")

    @channels_app.command("create")
    def channels_create(
        target: str = typer.Option(..., help="e.g. a Telegram chat id"),
        channel_type: str = typer.Option("TELEGRAM"),
    ) -> None:
        channel = ctx.create_channel.run(
            user_id=ctx.user_id(),
            channel_type=ChannelType(channel_type.upper()),
            target=target,
        )
        typer.echo(f"Created channel {channel.id} ({channel.channel_type.value} -> {target})")

    @channels_app.command("list")
    def channels_list() -> None:
        for channel in ctx.list_channels.run(user_id=ctx.user_id()):
            status = "enabled" if channel.is_enabled else "disabled"
            typer.echo(f"{channel.id}  {channel.channel_type.value}  {channel.target}  [{status}]")

    @app.command("list-matches")
    def list_matches(limit: int = typer.Option(20)) -> None:
        for view in ctx.list_matches.run(user_id=ctx.user_id(), limit=limit):
            typer.echo(_format_match_view(view))

    @app.command("run-cycle")
    def run_cycle() -> None:
        typer.echo(_format_cycle_report(ctx.planner_tick.run()))

    @app.command("dispatch")
    def dispatch() -> None:
        typer.echo(_format_dispatch_report(ctx.dispatch_notifications.run()))

    @app.command("serve")
    def serve() -> None:
        typer.echo("Starting scheduler (planner + dispatcher)... Ctrl+C to stop.")
        ctx.run_scheduler_forever()

    return app


def _format_match_view(view: MatchView) -> str:
    prop = view.property
    title = prop.title if prop is not None else "(property no longer available)"
    price = f"{prop.price.amount:,.0f} {prop.price.currency.value}" if prop and prop.price else "?"
    line = f"{view.match.matched_at}  {title}  {price}"
    if view.listing_url is not None:
        line += f"  {view.listing_url}"
    return line


def _format_cycle_report(report: RunAlertCycleReport) -> str:
    return (
        f"queries: {report.queries_planned} planned, {report.queries_succeeded} succeeded, "
        f"{report.queries_failed} failed; matches created: {report.matches_created}"
    )


def _format_dispatch_report(report: DispatchReport) -> str:
    return (
        f"notifications: {report.notifications_pending} pending, "
        f"{report.sent} sent, {report.failed} failed"
    )
