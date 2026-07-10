"""ListAlerts — every alert owned by a user."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.ports import UnitOfWork


class ListAlerts:
    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(self, *, user_id: UserId) -> Sequence[SearchAlert]:
        with self._uow_factory() as uow:
            return uow.alerts.list_for_user(user_id)
