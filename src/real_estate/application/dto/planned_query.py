"""PlannedQuery: one deduplicated portal query, and every alert that shares it."""

from __future__ import annotations

from dataclasses import dataclass

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.ports.scraper import PortalQuery


@dataclass(frozen=True, slots=True)
class PlannedQuery:
    """The output of :class:`SearchPlanner`: fetch ``query`` once, evaluate
    every alert in ``alerts`` against the result (docs/architecture/06-search-scheduler.md §3).
    """

    portal_slug: str
    signature: str
    query: PortalQuery
    alerts: tuple[SearchAlert, ...]
