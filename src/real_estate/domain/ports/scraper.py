"""Scraper port and its boundary DTOs.

A ``Scraper`` fetches raw, portal-shaped listings for a query. It performs **no**
cleaning — that is the Normalizer's job — so the captured ``RawListing`` can be
replayed/re-normalized later (docs/architecture/05-normalization.md).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PortalQuery:
    """A portal search reduced to its server-side (pushable) parameters.

    ``params`` are the coarse filters the portal can apply itself. The canonical
    dedup *signature* is computed from these by the search planner (Phase 5).
    """

    portal_slug: str
    params: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawListing:
    """A faithful capture of one listing exactly as a portal returned it."""

    portal_slug: str
    external_id: str
    url: str
    scraped_at: datetime
    raw: Mapping[str, Any] = field(default_factory=dict)


class Scraper(Protocol):
    """Fetches raw listings from a single portal."""

    portal_slug: str

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        """Return the raw listings matching ``query`` (may be empty)."""
        ...
