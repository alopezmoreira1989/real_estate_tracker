"""ListMatches — the most recent matches across every alert owned by a user."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.domain.model.identifiers import UserId
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.ports import UnitOfWork


class ListMatches:
    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(self, *, user_id: UserId, limit: int = 20) -> Sequence[AlertMatch]:
        with self._uow_factory() as uow:
            return uow.matches.list_recent_for_user(user_id, limit=limit)
