"""MatchView — a match enriched enough to be read by a human.

``AlertMatch`` alone carries only a ``property_id`` UUID, useless in a CLI
listing or a dashboard table built for eyeballing results (roadmap Phase 8's
stated exit criterion). ``ListMatches`` resolves the ``Property`` and its
originating listing url alongside each match.
"""

from __future__ import annotations

from dataclasses import dataclass

from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.property import Property


@dataclass(frozen=True, slots=True)
class MatchView:
    match: AlertMatch
    property: Property | None
    listing_url: str | None
