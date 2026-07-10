"""Streamlit dashboard — the dev-facing verification UI (roadmap Phase 8):
create/edit alerts, eyeball recent matches, and check scrape/normalization
health. Every action calls the exact same application use-cases the CLI
does — this is not a second implementation of the platform's logic, just a
second window onto it.

Run with: ``streamlit run src/real_estate/dashboard.py`` (that tiny script
builds a :class:`DashboardContext` via the composition root and calls
:func:`render` here). This module itself only imports ``streamlit`` plus
``application``/``domain`` — never ``real_estate.composition`` or
``real_estate.infrastructure`` — mirroring how ``CliContext`` is defined in
``presentation/cli/app.py`` and built *by* composition.py, not the reverse.
Streamlit's own script must be the literal process entry point, which is
why a separate bootstrap script exists instead of this module building its
own dependencies the way the CLI's ``__main__.py`` does.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.application.use_cases.list_alerts import ListAlerts
from real_estate.application.use_cases.list_channels import ListChannels
from real_estate.application.use_cases.list_matches import ListMatches
from real_estate.application.use_cases.list_search_executions import ListSearchExecutions
from real_estate.application.use_cases.update_alert import AlertNotFoundError, UpdateAlert
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import AlertCondition, RuleGroup
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.model.notification_channel import ChannelType
from real_estate.domain.vocabulary import PropertyType, Province

_PROPERTY_TYPE_LABELS: dict[PropertyType, str] = {
    PropertyType.FLAT: "Apartment",
    PropertyType.PENTHOUSE: "Penthouse",
    PropertyType.DUPLEX: "Duplex",
    PropertyType.STUDIO: "Studio",
    PropertyType.HOUSE: "House",
    PropertyType.CHALET: "Chalet",
    PropertyType.LAND: "Terrain / land",
    PropertyType.GARAGE: "Garage",
    PropertyType.STORAGE_ROOM: "Storage room / basement",
    PropertyType.OFFICE: "Office",
    PropertyType.COMMERCIAL: "Commercial premises",
    PropertyType.BUILDING: "Building",
}
_FREQUENCY_HOURS_OPTIONS = [1, 2, 3, 4, 6, 8, 12, 24]
_OTHER_PORTALS = ("Milanuncios", "Fotocasa", "Pisos.com")


@dataclass(frozen=True, slots=True)
class DashboardContext:
    """Every use-case the dashboard needs, built once by composition.py."""

    user_id: Callable[[], UserId]
    create_alert: CreateAlert
    update_alert: UpdateAlert
    list_alerts: ListAlerts
    list_matches: ListMatches
    create_channel: CreateChannel
    list_channels: ListChannels
    list_search_executions: ListSearchExecutions


def _province_options() -> list[Province]:
    return sorted((p for p in Province if p is not Province.UNKNOWN), key=lambda p: p.display_name)


def _property_type_options() -> list[PropertyType]:
    return [t for t in PropertyType if t in _PROPERTY_TYPE_LABELS]


def _price_conditions(field: str, low: float, high: float) -> list[str]:
    """Build FIELD:OPERATOR:VALUE strings for an optional min/max range (0 = unset)."""
    conditions = []
    if low and high:
        conditions.append(f"{field}:BETWEEN:{low:.0f},{high:.0f}")
    elif low:
        conditions.append(f"{field}:GTE:{low:.0f}")
    elif high:
        conditions.append(f"{field}:LTE:{high:.0f}")
    return conditions


def _portal_picker(key_prefix: str) -> frozenset[str]:
    st.caption("Portals")
    columns = st.columns(4)
    idealista = columns[0].checkbox("Idealista", value=True, key=f"{key_prefix}_idealista")
    for column, portal_name in zip(columns[1:], _OTHER_PORTALS, strict=True):
        column.checkbox(
            portal_name,
            value=False,
            disabled=True,
            help="Scraper not built yet — Idealista is the only portal live today.",
            key=f"{key_prefix}_{portal_name}",
        )
    return frozenset({"idealista"}) if idealista else frozenset()


def _render_alerts(ctx: DashboardContext) -> None:
    st.subheader("Your alerts")
    alerts = ctx.list_alerts.run(user_id=ctx.user_id())
    if not alerts:
        st.info("No alerts yet — create one below.")
    for alert in alerts:
        status = "🟢 active" if alert.is_active else "⚪ paused"
        hours = alert.frequency_seconds / 3600
        with st.expander(f"{alert.name} — {status} — every {hours:g}h"):
            _render_edit_form(ctx, alert)

    st.divider()
    st.subheader("Create a new alarm")
    with st.form("create_alert_form", clear_on_submit=True):
        name = st.text_input("Alarm name", placeholder="e.g. Land in Pontevedra under 20 EUR/m2")
        portals = _portal_picker("create")

        col1, col2 = st.columns(2)
        property_type = col1.selectbox(
            "Property type",
            options=_property_type_options(),  # type: ignore[arg-type]
            format_func=_PROPERTY_TYPE_LABELS.get,  # type: ignore[arg-type]
        )
        listing_type = col2.radio("Operation", ["SALE", "RENT"], horizontal=True)
        province = st.selectbox(
            "Province", options=_province_options(), format_func=lambda p: p.display_name
        )
        # selectbox can only return None for an empty options list or index=None; neither
        # applies here (both option lists are non-empty, no explicit index override).
        assert property_type is not None
        assert province is not None

        col3, col4 = st.columns(2)
        price_min = col3.number_input("Price from (EUR)", min_value=0, step=5000, value=0)
        price_max = col4.number_input("Price up to (EUR)", min_value=0, step=5000, value=0)
        col5, col6 = st.columns(2)
        ppm2_min = col5.number_input("Price/m2 from (EUR)", min_value=0, step=5, value=0)
        ppm2_max = col6.number_input("Price/m2 up to (EUR)", min_value=0, step=5, value=0)

        frequency_hours = st.select_slider("Check every", options=_FREQUENCY_HOURS_OPTIONS, value=4)
        submitted = st.form_submit_button("Create alarm", type="primary")

        if submitted:
            if not name.strip():
                st.error("Give the alarm a name.")
            elif not portals:
                st.error("At least one portal must be selected.")
            else:
                conditions = [
                    f"province:EQ:{province.code}",
                    f"property_type:EQ:{property_type.value}",
                    f"listing_type:EQ:{listing_type}",
                    *_price_conditions("price", price_min, price_max),
                    *_price_conditions("price_per_m2", ppm2_min, ppm2_max),
                ]
                ctx.create_alert.run(
                    user_id=ctx.user_id(),
                    name=name,
                    portal_slugs=portals,
                    frequency_seconds=int(frequency_hours * 3600),
                    condition_strings=conditions,
                )
                st.success(f"Created {name!r}.")
                st.rerun()


def _format_condition(node: AlertCondition | RuleGroup) -> str:
    if isinstance(node, RuleGroup):
        # AND-only for the MVP (ADR-014): every condition this dashboard/CLI ever writes is a
        # flat leaf, never a nested group — this branch only guards the type, not real data.
        return f"({node.operator.value} of {len(node.children)} nested conditions)"
    return f"{node.field_key} {node.operator.value} {node.value}"


def _render_edit_form(ctx: DashboardContext, alert: SearchAlert) -> None:
    st.caption("Current conditions")
    st.code(
        "\n".join(_format_condition(c) for c in alert.conditions.children),
        language=None,
    )

    with st.form(f"edit_{alert.id}"):
        name = st.text_input("Name", value=alert.name)
        current_hours = alert.frequency_seconds
        closest_hours = min(_FREQUENCY_HOURS_OPTIONS, key=lambda h: abs(h * 3600 - current_hours))
        hours = st.select_slider(
            "Check every", options=_FREQUENCY_HOURS_OPTIONS, value=closest_hours
        )
        is_active = st.checkbox("Active", value=alert.is_active)
        raw_conditions = st.text_area(
            "Conditions (FIELD:OPERATOR:VALUE, one per line) — leave blank to keep as-is",
            placeholder="province:EQ:36\nprice_per_m2:LTE:20",
        )
        submitted = st.form_submit_button("Save changes")

        if submitted:
            try:
                ctx.update_alert.run(
                    alert_id=alert.id,
                    name=name if name != alert.name else None,
                    frequency_seconds=int(hours * 3600),
                    is_active=is_active,
                    condition_strings=(
                        [line for line in raw_conditions.splitlines() if line.strip()]
                        if raw_conditions.strip()
                        else None
                    ),
                )
                st.success("Saved.")
                st.rerun()
            except AlertNotFoundError:
                st.error("This alert no longer exists.")


def _render_matches(ctx: DashboardContext) -> None:
    st.subheader("Recent matches")
    views = ctx.list_matches.run(user_id=ctx.user_id(), limit=50)
    if not views:
        st.info(
            "No matches yet — run a cycle (`python -m real_estate run-cycle`) once an alert exists."
        )
        return

    rows = []
    for view in views:
        prop = view.property
        price = "—"
        if prop is not None and prop.price is not None:
            price = f"{prop.price.amount:,.0f} {prop.price.currency.value}"
        area = f"{prop.area.square_meters:,.0f}" if prop and prop.area else "—"
        rows.append(
            {
                "Matched at": view.match.matched_at,
                "Title": prop.title if prop else "(unavailable)",
                "Price": price,
                "Area (m2)": area,
                "Province": prop.location.province.display_name if prop else "—",
                "Listing": view.listing_url,
            }
        )
    st.dataframe(
        rows,
        column_config={"Listing": st.column_config.LinkColumn("Listing", display_text="Open ↗")},
        hide_index=True,
        width="stretch",
    )


def _render_health(ctx: DashboardContext) -> None:
    st.subheader("Scrape & normalization health")
    executions = ctx.list_search_executions.run(limit=50)
    if not executions:
        st.info("No scrapes recorded yet.")
        return

    total_found = sum(e.listings_found for e in executions)
    total_issues = sum(e.normalization_issues for e in executions)
    issue_rate = (total_issues / total_found) if total_found else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Executions (recent)", len(executions))
    col2.metric("Listings found", total_found)
    col3.metric("Normalization issue rate", f"{issue_rate:.1%}")

    st.dataframe(
        [
            {
                "Started": e.started_at,
                "Portal": e.portal_slug,
                "Status": e.status.value,
                "Found": e.listings_found,
                "New": e.listings_new,
                "Issues": e.normalization_issues,
                "Error": e.error or "",
            }
            for e in executions
        ],
        hide_index=True,
        width="stretch",
    )


def _render_channels(ctx: DashboardContext) -> None:
    st.subheader("Notification channels")
    channels = ctx.list_channels.run(user_id=ctx.user_id())
    if not channels:
        st.info("No channels yet — create one below.")
    st.dataframe(
        [
            {
                "Type": c.channel_type.value,
                "Target": c.target,
                "Status": "enabled" if c.is_enabled else "disabled",
            }
            for c in channels
        ],
        hide_index=True,
        width="stretch",
    )

    st.divider()
    with st.form("create_channel_form", clear_on_submit=True):
        target = st.text_input("Telegram chat id", placeholder="123456789")
        submitted = st.form_submit_button("Create channel", type="primary")
        if submitted:
            if not target.strip():
                st.error("A chat id is required.")
            else:
                ctx.create_channel.run(
                    user_id=ctx.user_id(), channel_type=ChannelType.TELEGRAM, target=target
                )
                st.success("Channel created.")
                st.rerun()


def render(ctx: DashboardContext) -> None:
    """Render the whole dashboard. Called by the bootstrap script (dashboard.py)."""
    st.set_page_config(page_title="Real Estate Alert Platform", page_icon="🏠", layout="wide")
    st.title("🏠 Real Estate Alert Platform")
    st.caption(
        "Dev-facing verification dashboard (Phase 8) — every action here calls the same "
        "application use-cases as the CLI. Only Idealista is a live portal today."
    )

    tabs = st.tabs(["Alerts", "Matches", "Health", "Channels"])
    with tabs[0]:
        _render_alerts(ctx)
    with tabs[1]:
        _render_matches(ctx)
    with tabs[2]:
        _render_health(ctx)
    with tabs[3]:
        _render_channels(ctx)
