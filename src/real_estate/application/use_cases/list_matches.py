"""ListMatches — the most recent matches across every alert owned by a user,
enriched with the matched Property and its listing url (MatchView) so the
result is actually readable in a CLI list or a dashboard table.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.application.dto import MatchView
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.ports import UnitOfWork


class ListMatches:
    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(self, *, user_id: UserId, limit: int = 20) -> Sequence[MatchView]:
        with self._uow_factory() as uow:
            matches = uow.matches.list_recent_for_user(user_id, limit=limit)
            return [
                MatchView(
                    match=match,
                    property=uow.properties.get(match.property_id),
                    listing_url=uow.portal_listings.get_url_for_property(match.property_id),
                )
                for match in matches
            ]
