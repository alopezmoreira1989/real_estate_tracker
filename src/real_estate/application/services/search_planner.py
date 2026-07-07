"""SearchPlanner — turns due alerts into the fewest possible portal queries.

Driver D3: ten alerts on the same search must yield one scrape, not ten. For
each alert and each portal it monitors, splits the alert's **top-level**
condition group into portal-pushable params (coarse, shared widely) vs.
everything else — the Rule Engine always evaluates the alert's *full*
Specification client-side after fetch regardless (doc06 §1), so this only
narrows what gets downloaded, never what counts as a match. Alerts that
reduce to the same ``(portal_slug, signature)`` are grouped into one
:class:`PlannedQuery` (doc06 §2).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from real_estate.application.dto import PlannedQuery
from real_estate.application.ports import PortalCapabilities
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import AlertCondition, GroupOperator, Operator
from real_estate.domain.ports.scraper import PortalQuery

# Fields pushable as a single EQ filter (portal_slug's own vocabulary term is
# resolved later, by the scraper — the planner only ever handles canonical
# values, e.g. an INE province code or a PropertyType.value string).
_EQ_PUSHABLE_FIELDS = frozenset({"province", "property_type", "listing_type"})


class SearchPlanner:
    """Splits due alerts into pushable/client-side conditions and dedups by signature."""

    def __init__(self, capabilities: Mapping[str, PortalCapabilities]) -> None:
        self._capabilities = capabilities

    def plan(self, due_alerts: Sequence[SearchAlert]) -> Sequence[PlannedQuery]:
        groups: dict[tuple[str, str], tuple[dict[str, str], list[SearchAlert]]] = {}

        for alert in due_alerts:
            for portal_slug in sorted(alert.portal_slugs):
                params = self._pushable_params(alert, portal_slug)
                signature = self._signature(portal_slug, params)
                key = (portal_slug, signature)
                if key not in groups:
                    groups[key] = (params, [])
                groups[key][1].append(alert)

        return [
            PlannedQuery(
                portal_slug=portal_slug,
                signature=signature,
                query=PortalQuery(portal_slug=portal_slug, params=params),
                alerts=tuple(alerts),
            )
            for (portal_slug, signature), (params, alerts) in groups.items()
        ]

    def _pushable_params(self, alert: SearchAlert, portal_slug: str) -> dict[str, str]:
        capabilities = self._capabilities.get(portal_slug)
        top = alert.conditions
        if capabilities is None or top.operator is not GroupOperator.ALL:
            # Unknown portal, or a top-level OR/NOT the planner won't safely
            # reduce to a portal-side filter — fetch broad, filter client-side.
            return {}

        params: dict[str, str] = {}
        for child in top.children:
            if isinstance(child, AlertCondition):
                self._add_if_pushable(params, child, capabilities)
            # Nested groups aren't decomposed for MVP (AND-only UI, ADR-014).
        return params

    @staticmethod
    def _add_if_pushable(
        params: dict[str, str], condition: AlertCondition, capabilities: PortalCapabilities
    ) -> None:
        if condition.field_key not in capabilities.pushable_fields:
            return

        if condition.field_key in _EQ_PUSHABLE_FIELDS:
            if condition.operator is Operator.EQ:
                params[condition.field_key] = str(condition.value)
            return

        if condition.field_key == "price":
            if condition.operator is Operator.LTE:
                params["price_max"] = str(condition.value)
            elif condition.operator is Operator.GTE:
                params["price_min"] = str(condition.value)
            elif condition.operator is Operator.BETWEEN and isinstance(condition.value, tuple):
                low, high = condition.value
                params["price_min"] = str(low)
                params["price_max"] = str(high)

    @staticmethod
    def _signature(portal_slug: str, params: Mapping[str, str]) -> str:
        canonical = "&".join(f"{key}={value}" for key, value in sorted(params.items()))
        return hashlib.sha256(f"{portal_slug}|{canonical}".encode()).hexdigest()
